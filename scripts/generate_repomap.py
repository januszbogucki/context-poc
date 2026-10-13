#!/usr/bin/env python3
"""Generuje mapę repozytorium (klasy i sygnatury metod) do pliku Markdown.

Używa klasy RepoMap z narzędzia RepoMapper (https://github.com/pdavis68/RepoMapper).
Własny skrypt jest potrzebny, bo CLI RepoMappera drukuje krotkę (tekst, raport) zamiast samego tekstu.

Użycie: generate_repomap.py <katalog_RepoMappera> <wyjściowy_plik.md>
Uruchamiany z katalogu głównego repozytorium. Pliki bierze z `git ls-files`, więc pomija vendor/ i var/.
"""

import fnmatch
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MAP_TOKENS = 4096
EXCLUDE_FILE = Path(__file__).with_name("repomap-exclude.txt")
EXTENSIONS = (".php",)

HEADER = """# Mapa repozytorium (wygenerowana automatycznie)

Plik generuje `scripts/update-context.sh` (lokalnie lub w GitHub Action `update-context`).
**Nie edytuj ręcznie**, zmiany zostaną nadpisane przy następnym uruchomieniu.

Zawiera klasy i sygnatury metod z numerami linii. Nie opisuje powiązań między klasami ani reguł biznesowych.

"""


def sort_blocks(lines: list[str]) -> list[str]:
    """Dzieli wynik na bloki (jeden na plik) i sortuje po nazwie pliku.

    RepoMapper zwraca pliki w niestabilnej kolejności, a przy każdej różnicy w pliku CI otwierałoby PR.
    Nagłówek bloku to linia bez wcięcia kończąca się dwukropkiem.
    """
    blocks: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line and not line[0].isspace() and line.endswith(":"):
            current = line
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return [header + "\n" + "\n".join(body).strip("\n") for header, body in sorted(blocks.items())]


def load_exclude_patterns() -> list[str]:
    """Wzorce z scripts/repomap-exclude.txt (jeden na linię, # to komentarz)."""
    if not EXCLUDE_FILE.is_file():
        return []
    lines = (line.strip() for line in EXCLUDE_FILE.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def is_excluded(path: str, patterns: list[str]) -> bool:
    """Wzorzec pasuje do ścieżki względem repo albo do samej nazwy pliku, bez rozróżniania wielkości liter
    (nazwy klas w PHP zaczynają się wielką literą, np. StripeCredentials.php)."""
    path = path.lower()
    name = path.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatchcase(path, p.lower()) or fnmatch.fnmatchcase(name, p.lower()) for p in patterns
    )


def main() -> None:
    mapper_dir, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    repo_root = Path.cwd().resolve()
    sys.path.insert(0, str(mapper_dir))

    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    candidates = [f for f in tracked if f.endswith(EXTENSIONS) and (repo_root / f).is_file()]
    patterns = load_exclude_patterns()
    excluded = [f for f in candidates if is_excluded(f, patterns)]
    files = sorted(str(repo_root / f) for f in candidates if f not in excluded)
    print(f"wzorce wykluczeń: {len(patterns)}, wykluczono plików: {len(excluded)}")
    for f in excluded:
        print(f"  pominięto {f}")

    # RepoMapper zapisuje cache w katalogu bieżącym z chwili importu, więc najpierw przechodzimy
    # do katalogu tymczasowego, a dopiero potem importujemy.
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        from repomap_class import RepoMap
        from utils import count_tokens, read_text

        repo_map = RepoMap(
            map_tokens=MAP_TOKENS,
            root=str(repo_root),
            token_counter_func=lambda text: count_tokens(text, "gpt-4"),
            file_reader_func=read_text,
            output_handler_funcs={
                "info": lambda *a: None,
                "warning": lambda m: print(f"warning: {m}", file=sys.stderr),
                "error": lambda m: print(f"error: {m}", file=sys.stderr),
            },
        )
        content, report = repo_map.get_repo_map(chat_files=[], other_files=files)

    if not content:
        sys.exit("RepoMapper nie zwrócił mapy")

    # Linie "(Rank value: ...)" nic nie wnoszą (wszystkie pliki mają tę samą wartość) i szumią w diffie.
    lines = [line for line in content.splitlines() if not line.startswith("(Rank value:")]
    body = "\n\n".join(sort_blocks(lines))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(HEADER + "```\n" + body + "\n```\n", encoding="utf-8")
    print(f"zapisano {output.relative_to(repo_root)} ({len(files)} plików)")


if __name__ == "__main__":
    main()
