#!/usr/bin/env bash
# Odświeża kontekst repozytorium: docs/context/repomap.md.
# Ten sam skrypt uruchamiasz ręcznie na starcie i wywołuje go GitHub Action (.github/workflows/update-context.yml).
set -euo pipefail

# Wersja RepoMappera (commit). Zmiana wersji = świadoma decyzja, bo to kod z zewnątrz.
REPOMAPPER_URL="https://github.com/pdavis68/RepoMapper.git"
REPOMAPPER_REF="3ef8914b3a2271695ac9e4b07ce1e8bf5a4c9be6"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/.context-tools"
MAPPER_DIR="$TOOLS_DIR/RepoMapper"
VENV_DIR="$TOOLS_DIR/venv"

# W GitHub Actions ::group:: zwija linie w sekcję w logu. Lokalnie wypisujemy zwykły nagłówek.
step() {
    if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::group::$*"; else echo "==> $*"; fi
}
end_step() {
    if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::endgroup::"; fi
}

step "1/3 Pobieranie narzędzia RepoMapper (commit ${REPOMAPPER_REF:0:7})"
mkdir -p "$TOOLS_DIR"
if [ ! -d "$MAPPER_DIR/.git" ]; then
    echo "Klonuję $REPOMAPPER_URL"
    git clone --quiet "$REPOMAPPER_URL" "$MAPPER_DIR"
fi
git -C "$MAPPER_DIR" fetch --quiet origin "$REPOMAPPER_REF" 2>/dev/null || true
git -C "$MAPPER_DIR" checkout --quiet "$REPOMAPPER_REF"
echo "Narzędzie na commicie: $(git -C "$MAPPER_DIR" rev-parse --short HEAD)"
end_step

step "2/3 Instalacja zależności Pythona (wersje przypięte)"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --quiet --requirement "$REPO_ROOT/scripts/repomap-requirements.txt"
echo "Python: $("$VENV_DIR/bin/python" --version)"
grep -v '^#' "$REPO_ROOT/scripts/repomap-requirements.txt" | sed 's/^/  /'
end_step

step "3/3 Generowanie mapy repozytorium"
cd "$REPO_ROOT"
"$VENV_DIR/bin/python" scripts/generate_repomap.py "$MAPPER_DIR" docs/context/repomap.md
echo "Wynik: docs/context/repomap.md ($(wc -l < docs/context/repomap.md) linii, $(wc -c < docs/context/repomap.md) bajtów)"
end_step
