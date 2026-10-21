#!/usr/bin/env python3
"""Generuje kontekst kodu aplikacji z katalogu src/.

Opis uzupełniają pliki PHP z config/ i public/, composer.json, data/products.json
oraz mapa repozytorium, z uwzględnieniem scripts/repomap-exclude.txt.
Uwierzytelnianie: token Claude/Codex w CI albo lokalne logowanie ChatGPT.
"""

import argparse
import os
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from generate_repomap import is_excluded, load_exclude_patterns
from context_stats import GenerationStats

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = (
    "## Architektura", "## Przepływy", "## Reguły biznesowe",
    "## Dane i API", "## Praca z projektem", "## Ograniczenia",
)


def source_files(root: Path) -> dict[str, str]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    patterns = load_exclude_patterns()
    selected = sorted(
        name for name in tracked
        if name and not is_excluded(name, patterns)
        and (name == "composer.json" or name == "data/products.json"
             or (name.startswith(("src/", "config/", "public/")) and name.endswith(".php")))
    )
    files = {}
    for name in selected:
        path = root / name
        # Nie podążaj za symlinkami poza zatwierdzony zestaw plików.
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Niedozwolona ścieżka wejściowa: {name}")
        if not path.is_file():
            continue  # Lokalne usunięcie może jeszcze nie być dodane do indeksu git.
        files[name] = path.read_text(encoding="utf-8")
    return files


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def claude_credential() -> tuple[str, str] | None:
    """Klucz API Claude ma pierwszeństwo przed tokenem subskrypcji (OAuth)."""
    for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return None


def select_provider(provider: str = "auto", auth: str = "token") -> str:
    if provider not in ("auto", "codex", "claude"):
        raise ValueError("Nieznany dostawca modelu.")
    if auth == "chatgpt":
        if provider == "claude":
            raise ValueError("Logowanie ChatGPT jest dostępne tylko dla Codex.")
        return "codex"
    if provider != "auto":
        return provider
    if claude_credential():
        return "claude"
    if os.environ.get("CODEX_ACCESS_TOKEN", "").strip():
        return "codex"
    return "none"


def generate(root: Path = ROOT, auth: str = "token", provider: str = "auto", force: bool = False) -> None:
    if auth not in ("token", "chatgpt"):
        raise ValueError("Nieznany tryb logowania.")
    if auth == "chatgpt" and os.environ.get("GITHUB_ACTIONS") == "true":
        raise ValueError("Logowanie ChatGPT służy tylko do pracy lokalnej; CI wymaga tokena.")
    provider = select_provider(provider, auth)
    if provider == "none":
        raise ValueError(
            "Brak tokena: ustaw ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN lub CODEX_ACCESS_TOKEN "
            "według docs/CONTEXT-SETUP.md."
        )
    if provider == "claude":
        token_name, token = claude_credential() or ("CLAUDE_CODE_OAUTH_TOKEN", "")
    else:
        token_name = "CODEX_ACCESS_TOKEN"
        token = os.environ.get(token_name, "").strip()
    if auth == "token" and not token:
        raise ValueError(
            f"Brak {token_name}. Dodaj sekret repozytorium według docs/CONTEXT-SETUP.md."
        )
    generator_name = "Claude" if provider == "claude" else "Codex"
    prompt = (root / "docs/context/instructions.md").read_text(encoding="utf-8")
    files = source_files(root)
    hashes = {name: digest(content) for name, content in files.items()}
    output_directory = root / "docs/context" / provider
    destination = output_directory / "application.md"
    state_path = output_directory / "application-state.json"
    state = {}
    if state_path.is_file() and destination.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass  # Brak poprawnego stanu oznacza pełną odbudowę.
    full = force or not (
        isinstance(state, dict) and state.get("version") == 1
        and isinstance(state.get("files"), dict)
        and state.get("prompt_sha256") == digest(prompt)
        and state.get("provider", "codex") == provider
        and state.get("context_sha256") == digest(destination.read_text(encoding="utf-8"))
    )
    previous = {} if full else state["files"]
    changed = sorted(name for name in hashes if previous.get(name) != hashes[name])
    removed = sorted(set(previous) - set(hashes))
    if not full and not changed and not removed:
        print(f"Źródła bez zmian: pominięto wywołanie {generator_name}.")
        return
    parts = ["TRYB: pełna budowa" if full else "TRYB: aktualizacja przyrostowa"]
    if not full:
        parts.append("POPRZEDNI KONTEKST:\n" + destination.read_text(encoding="utf-8"))
    parts.append("USUNIĘTE PLIKI:\n" + ("\n".join(removed) or "brak"))
    parts.append("AKTUALNA MAPA:\n" + (root / "docs/context/repomap.md").read_text(encoding="utf-8"))
    parts.extend(f"\n--- PLIK DODANY LUB ZMIENIONY: {name} ---\n{files[name]}" for name in changed)
    bundle = "\n\n".join(parts)
    if len(bundle.encode("utf-8")) > 500_000:
        raise ValueError("Wejście przekracza limit POC 500 KB; zawęź listę plików.")
    print(f"Dostawca: {generator_name}; tryb: {'pełny' if full else 'przyrostowy'}; pliki do analizy: {len(changed)}, usunięte: {len(removed)}")
    # Pusty katalog roboczy: bez konfiguracji projektu, .git i poświadczeń GitHub.
    # CI ma osobny CODEX_HOME; tryb lokalny używa istniejącego logowania CLI.
    with tempfile.TemporaryDirectory(prefix="application-context-") as directory:
        temporary = Path(directory)
        home = temporary / "codex-home"
        home.mkdir(mode=0o700)
        output = temporary / "application.md"
        environment = {
            key: value for key, value in os.environ.items()
            if key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT")
        }
        if provider == "claude":
            claude_home = temporary / "claude-home"
            claude_home.mkdir(mode=0o700)
            environment.update(
                {token_name: token}, CLAUDE_CONFIG_DIR=str(claude_home),
                DISABLE_AUTOUPDATER="1",
            )
        elif auth == "token":
            environment.update(CODEX_ACCESS_TOKEN=token, CODEX_HOME=str(home))
        else:
            if os.environ.get("CODEX_HOME"):
                environment["CODEX_HOME"] = os.environ["CODEX_HOME"]
            login = subprocess.run(
                ["codex", "login", "status"], cwd=temporary, env=environment,
                capture_output=True, text=True, timeout=30,
            )
            if login.returncode or "chatgpt" not in (login.stdout + login.stderr).lower():
                raise ValueError("Brak logowania ChatGPT. Uruchom codex login i wybierz konto Business.")
        if provider == "claude":
            # OAuth subskrypcji nie działa z --bare. Osobny katalog konfiguracji,
            # wyłączone narzędzia i MCP zapewniają tryb analizy samego stdin.
            command = [
                "claude", "--print", "--output-format", "json", "--tools", "",
                "--disallowedTools", "mcp__*", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
                "--no-session-persistence", "--max-turns", "1",
            ]
        else:
            command = ["codex", "exec", "--json", "--sandbox", "read-only", "--ephemeral",
             "--ignore-user-config", "--skip-git-repo-check", "--color", "never",
             "-c", 'shell_environment_policy.inherit="none"',
             "--output-last-message", str(output), "-"]
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        with GenerationStats(
            output_directory, provider, mode="full" if full else "incremental",
            files_analyzed=len(changed), files_removed=len(removed), files_total=len(files),
            source_commit=commit,
        ) as stats:
            result = subprocess.run(
                command, cwd=temporary, env=environment,
                input=prompt.replace("{{GENERATOR}}", generator_name) + "\n\n" + bundle,
                text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=600,
            )
            stats.transcript = result.stdout or ""
            if result.returncode:
                # Nie publikuj transkryptu/modelowego wyjścia w publicznych logach CI.
                raise ValueError(
                    f"{generator_name} zakończył się kodem {result.returncode}. Sprawdź logowanie/token, "
                    "uprawnienia, wersję CLI, połączenie sieciowe i limity subskrypcji. "
                    "Transkrypt pominięto, aby nie publikować źródeł ani poświadczeń."
                )
            if provider == "claude":
                try:
                    response = json.loads(result.stdout)
                except (ValueError, TypeError):
                    raise ValueError("Claude zwrócił niepoprawny JSON; poprzedni kontekst zachowano.") from None
                if not isinstance(response, dict) or response.get("is_error") is not False or response.get("subtype") != "success":
                    raise ValueError("Claude nie zakończył generowania sukcesem; poprzedni kontekst zachowano.")
                content = response.get("result", "")
            else:
                content = output.read_text(encoding="utf-8") if output.is_file() else ""
            if not isinstance(content, str):
                raise ValueError("Model zwrócił niepoprawny typ dokumentu.")
            if not content.startswith("# Kontekst aplikacji\n") or any(
                section not in content.splitlines() for section in SECTIONS
            ) or len(content) < 800 or len(content.encode("utf-8")) > 60_000:
                raise ValueError(f"{generator_name} zwrócił pusty lub niepoprawny dokument; poprzedni kontekst zachowano.")
            secrets = [os.environ.get(name, "").strip() for name in ("CODEX_ACCESS_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")]
            if any(secret and secret in content for secret in secrets):
                raise ValueError("Wynik zawiera poświadczenie; zapis zablokowany.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Publikuj dopiero kompletny, sprawdzony wynik.
            staged = destination.with_suffix(".md.tmp")
            staged.write_text(content.rstrip() + "\n", encoding="utf-8")
            staged.replace(destination)
            new_state = {
                "version": 1, "source_commit": commit, "files": hashes, "provider": provider,
                "prompt_sha256": digest(prompt),
                "context_sha256": digest(destination.read_text(encoding="utf-8")),
            }
            state_path.write_text(json.dumps(new_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Zapisano {destination.relative_to(root)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--auth", choices=("token", "chatgpt"), default="token",
        help="token: sekret CI; chatgpt: istniejące lokalne logowanie Codex CLI",
    )
    parser.add_argument(
        "--provider", choices=("auto", "claude", "codex"), default="auto",
        help="auto: najpierw token Claude, potem Codex; --auth chatgpt zawsze wybiera Codex",
    )
    parser.add_argument("--force", action="store_true", help="Wymuś pełne generowanie mimo braku zmian źródeł")
    arguments = parser.parse_args()
    try:
        generate(auth=arguments.auth, provider=arguments.provider, force=arguments.force)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Generowanie kontekstu nie powiodło się: {error}", file=sys.stderr)
        sys.exit(1)
