"""Pomiar tokenów z telemetrii CLI, bez zapisywania promptów i transkryptów."""

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = (
    "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens",
    "cache_creation_input_tokens", "reasoning_output_tokens",
)


def count(value):
    return value if type(value) is int and value >= 0 else None


def add(values):
    values = list(values)
    return sum(values) if values and all(value is not None for value in values) else None


def usage_from_cli(provider: str, transcript: str) -> dict:
    """input_tokens oznacza całe wejście; cache i reasoning są jego/wyjścia podzbiorami."""
    usage = dict.fromkeys(FIELDS)
    models = []
    if provider == "codex":
        turns = []
        for line in transcript.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                turns.append(event["usage"])
            if event.get("type") in ("thread.started", "turn.started") and isinstance(event.get("model"), str):
                models.append(event["model"])
        if turns:
            for field in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens"):
                usage[field] = add(count(turn.get(field)) for turn in turns)
            usage["total_tokens"] = add((usage["input_tokens"], usage["output_tokens"]))
    else:
        try:
            response = json.loads(transcript)
        except ValueError:
            response = {}
        if isinstance(response, dict):
            raw = response.get("usage")
            if isinstance(raw, dict):
                usage["cached_input_tokens"] = count(raw.get("cache_read_input_tokens"))
                usage["cache_creation_input_tokens"] = count(raw.get("cache_creation_input_tokens"))
                usage["input_tokens"] = add((
                    count(raw.get("input_tokens")), usage["cached_input_tokens"],
                    usage["cache_creation_input_tokens"],
                ))
                usage["output_tokens"] = count(raw.get("output_tokens"))
                usage["total_tokens"] = add((usage["input_tokens"], usage["output_tokens"]))
                details = raw.get("output_tokens_details")
                if isinstance(details, dict):
                    usage["reasoning_output_tokens"] = count(details.get("thinking_tokens"))
            if isinstance(response.get("modelUsage"), dict):
                models = list(response["modelUsage"])
    # Tylko identyfikatory modeli, bez dowolnych tekstów z wyniku modelu.
    models = sorted({model for model in models if isinstance(model, str)
                     and re.fullmatch(r"[a-zA-Z0-9._:/-]{1,128}", model)})
    return {"tokens": usage, "models": models}


def markdown(data: dict) -> str:
    runs = data["runs"]
    measured = [run for run in runs if run["tokens"]["total_tokens"] is not None]
    total = sum(run["tokens"]["total_tokens"] for run in measured)
    formatted_total = f"{total:,}".replace(",", " ")
    name = "Codex" if data["provider"] == "codex" else "Claude"
    lines = [
        f"# Statystyki generowania kontekstu — {name}", "",
        "Pomiar z telemetrii CLI. Historia obejmuje tylko przebiegi od włączenia pomiaru.",
        "Zużycie tokenów nie jest kwotą rachunku ani procentem limitu subskrypcji.", "",
        f"- Próby generowania: {len(runs)}.",
        f"- Zakończone sukcesem: {sum(run['status'] == 'success' for run in runs)}.",
        f"- Próby z pełnym pomiarem: {len(measured)}; bez pełnych danych: {len(runs) - len(measured)}.",
        f"- Suma tokenów w próbach z pełnym pomiarem: **{formatted_total}**.", "",
        "## Ostatnie przebiegi (maksymalnie 20)", "",
        "| Czas UTC | Status | Tryb | Pliki analizowane | Wejście | Wyjście | Razem | Cache odczyt | Cache zapis | Reasoning | Czas (s) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in reversed(runs[-20:]):
        tokens = run["tokens"]
        values = ["brak danych" if tokens[field] is None else str(tokens[field]) for field in FIELDS]
        lines.append(
            f"| {run['started_at']} | {run['status']} | {run['mode']} | {run['files_analyzed']} | "
            + " | ".join(values) + f" | {run['duration_seconds']} |"
        )
    lines += ["", "## Jak czytać liczby", "",
              "Wejście obejmuje także cache. Cache odczyt/zapis to części wejścia; nie dodawaj ich drugi raz.",
              "Reasoning, jeśli CLI go raportuje, jest częścią wyjścia; nie doliczaj go do sumy.",
              "Wejście + wyjście = razem. Brak danych oznacza brak pomiaru, a nie zero tokenów.",
              "Sumy obejmują również nieudane próby, jeśli CLI zwróciło dla nich pełne dane.",
              "Przebieg bez zmian źródeł nie uruchamia modelu i nie dopisuje statystyk.",
              "Pełna historia, commit źródłowy i nazwy modeli (o ile CLI je zwróciło) są w `stats.json`.", ""]
    return "\n".join(lines)


class GenerationStats:
    def __init__(self, directory: Path, provider: str, **metadata):
        self.directory = directory
        self.provider = provider
        self.metadata = metadata
        self.transcript = ""

    def __enter__(self):
        path = self.directory / "stats.json"
        self.data = {"version": 1, "provider": self.provider, "runs": []}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
                assert self.data["version"] == 1 and self.data["provider"] == self.provider
                assert isinstance(self.data["runs"], list)
                for run in self.data["runs"]:
                    assert all(field in run["tokens"] for field in FIELDS)
                    assert all(value is None or count(value) is not None for value in run["tokens"].values())
                    assert run["status"] in ("success", "failed") and run["mode"] in ("full", "incremental")
                    assert isinstance(run["started_at"], str) and count(run["files_analyzed"]) is not None
                    assert isinstance(run["duration_seconds"], (int, float))
            except (ValueError, TypeError, KeyError, AssertionError):
                raise ValueError(f"Niepoprawna historia statystyk: {path}. Przywróć ją przed generowaniem.") from None
        self.started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.started = time.monotonic()
        return self

    def __exit__(self, error_type, error, traceback):
        if isinstance(error, subprocess.TimeoutExpired) and error.stdout:
            self.transcript = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else error.stdout
        usage = usage_from_cli(self.provider, self.transcript)
        run = {
            **self.metadata, "started_at": self.started_at,
            "duration_seconds": round(time.monotonic() - self.started, 3),
            "status": "success" if error_type is None else "failed", **usage,
        }
        self.data["runs"].append(run)
        self.directory.mkdir(parents=True, exist_ok=True)
        for name, content in (
            ("stats.json", json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"),
            ("stats.md", markdown(self.data)),
        ):
            destination = self.directory / name
            staged = destination.with_suffix(destination.suffix + ".tmp")
            staged.write_text(content, encoding="utf-8")
            staged.replace(destination)
        total = usage["tokens"]["total_tokens"]
        print(f"Tokeny ({self.provider}): {total if total is not None else 'brak danych z CLI'}; raport: {self.directory / 'stats.md'}")
