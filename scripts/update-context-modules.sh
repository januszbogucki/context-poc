#!/usr/bin/env bash
# PRZYKŁAD: osobna mapa kontekstu dla każdego modułu w src/ (docs/context/modules/<Moduł>.md).
#
# Po co: w dużym projekcie jedna mapa całego repo nie zmieści się w budżecie tokenów, a Claude
# zwykle pracuje nad jednym modułem. Mapa modułu jest mała i można ją wczytać tylko wtedy, gdy jest potrzebna.
# Ten skrypt NIE jest podpięty do GitHub Action, to demonstracja (podpięcie to kilka linii w workflow).
#
# Użycie:
#   ./scripts/update-context-modules.sh                     # wszystkie moduły
#   MAP_TOKENS=1024 ./scripts/update-context-modules.sh     # mniejszy budżet na moduł (domyślnie 2048)
#   MODULES_DIR=app ./scripts/update-context-modules.sh     # inny katalog z modułami (domyślnie src)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODULES_DIR="${MODULES_DIR:-src}"
OUT_DIR="docs/context/modules"
export MAP_TOKENS="${MAP_TOKENS:-2048}"   # budżet tokenów PER MODUŁ (pełna mapa używa 4096)
EMPTY_EXIT_CODE=3                          # generate_repomap.py: moduł bez klas i funkcji

cd "$REPO_ROOT"

LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

# Narzędzie i wersje bierzemy z update-context.sh (jedno miejsce z przypiętym commitem RepoMappera),
# ale instalujemy je tutaj, żeby ten skrypt był samodzielny i nie zmieniał update-context.sh.
REPOMAPPER_URL="$(sed -n 's/^REPOMAPPER_URL="\(.*\)"/\1/p' scripts/update-context.sh)"
REPOMAPPER_REF="$(sed -n 's/^REPOMAPPER_REF="\(.*\)"/\1/p' scripts/update-context.sh)"
TOOLS_DIR="$REPO_ROOT/.context-tools"
MAPPER_DIR="$TOOLS_DIR/RepoMapper"
VENV_DIR="$TOOLS_DIR/venv"
PYTHON="$VENV_DIR/bin/python"

echo "==> Przygotowanie narzędzia RepoMapper (commit ${REPOMAPPER_REF:0:7})"
mkdir -p "$TOOLS_DIR"
[ -d "$MAPPER_DIR/.git" ] || git clone --quiet "$REPOMAPPER_URL" "$MAPPER_DIR"
git -C "$MAPPER_DIR" fetch --quiet origin "$REPOMAPPER_REF" 2>/dev/null || true
git -C "$MAPPER_DIR" checkout --quiet "$REPOMAPPER_REF"
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --requirement scripts/repomap-requirements.txt

echo "==> Generowanie map per moduł ($MODULES_DIR/*, budżet ${MAP_TOKENS} tokenów na moduł)"

# Usuwamy stare mapy, żeby po usunięciu modułu nie zostawały nieaktualne pliki.
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.md

index="$OUT_DIR/INDEX.md"
{
    echo "# Mapy modułów (wygenerowane automatycznie)"
    echo
    echo "Plik generuje \`scripts/update-context-modules.sh\`. **Nie edytuj ręcznie.**"
    echo "Każdy moduł ma osobną mapę klas i sygnatur. Wczytaj tylko ten moduł, nad którym pracujesz."
    echo
    echo "| Moduł | Plik z mapą | Plików PHP | Rozmiar |"
    echo "|---|---|---|---|"
} > "$index"

generated=0
skipped=0
for dir in "$MODULES_DIR"/*/; do
    [ -d "$dir" ] || continue
    module="$(basename "$dir")"
    out="$OUT_DIR/$module.md"

    set +e
    "$PYTHON" scripts/generate_repomap.py "$MAPPER_DIR" "$out" "$MODULES_DIR/$module" > "$LOG_FILE" 2>&1
    code=$?
    set -e

    if [ "$code" -eq "$EMPTY_EXIT_CODE" ]; then
        echo "  - $module: pominięty (RepoMapper nie zwrócił mapy: brak definicji albo moduł zawiera tylko interfejsy)"
        skipped=$((skipped + 1))
    elif [ "$code" -ne 0 ]; then
        echo "  - $module: BŁĄD (kod $code)" >&2
        cat "$LOG_FILE" >&2
        exit "$code"
    else
        files="$(git ls-files "$MODULES_DIR/$module" | grep -c '\.php$' || true)"
        bytes="$(wc -c < "$out")"
        echo "  - $module: $out (${files} plików PHP, ${bytes} bajtów)"
        echo "| $module | [$module.md]($module.md) | $files | ${bytes} B |" >> "$index"
        generated=$((generated + 1))
    fi
done

echo
echo "Gotowe: $generated map modułów, pominięto $skipped. Spis: $index"
echo "Uwaga: pliki leżące bezpośrednio w $MODULES_DIR/ (np. Kernel.php) nie należą do żadnego modułu,"
echo "są tylko w pełnej mapie z ./scripts/update-context.sh."
