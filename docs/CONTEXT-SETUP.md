# Kontekst aplikacji przez Claude lub Codex — konfiguracja POC

## Układ plików

```text
docs/
├── CONTEXT-SETUP.md               ← instrukcja obsługi i konfiguracji
└── context/
    ├── repomap.md                ← wspólna mapa z RepoMappera
    ├── instructions.md           ← wspólna instrukcja wejściowa dla modeli
    ├── codex/
    │   ├── application.md        ← wynik wygenerowany przez Codex
    │   ├── application-state.json
    │   ├── stats.md              ← czytelny raport zużycia tokenów
    │   └── stats.json            ← historia pomiarów
    └── claude/
        ├── application.md        ← powstaje po uruchomieniu Claude
        ├── application-state.json
        ├── stats.md
        └── stats.json
```

Na głównym poziomie `context/` są tylko dwa pliki wspólne. Każdy dostawca zapisuje
opis, stan i statystyki we własnym katalogu. Claude nie nadpisuje wyniku Codex i odwrotnie.
Nie tworzymy przykładowego wyniku Claude bez rzeczywistego generowania.

Plik do czytania jako kontekst aplikacji to `context/codex/application.md` albo
`context/claude/application.md`. Ten dokument objaśnia konfigurację mechanizmu.

Workflow `update-context` automatycznie wybiera dostawcę na podstawie nazw sekretów:

| Sekrety repozytorium | Dostawca generowania opisu |
|---|---|
| `ANTHROPIC_API_KEY` (klucz API, rozliczany za tokeny; ma pierwszeństwo) | Claude |
| `CLAUDE_CODE_OAUTH_TOKEN` (subskrypcja; także gdy jest token Codex) | Claude |
| Tylko `CODEX_ACCESS_TOKEN` | Codex |
| Brak obu tokenów | Sama mapa, bez wywołania modelu |

Sprawdzamy obecność tokenów, bez zgadywania ich typu z treści. Błąd Claude
(np. nieważny token lub limit) zatrzymuje przebieg; nie uruchamiamy wtedy
automatycznie Codex. Aby wybrać Codex w CI, usuń sekret Claude z repozytorium.
Podsumowanie workflow pokazuje wybranego dostawcę.

Tworzenie tokenów Codex w używanym workspace zwracało
`access_token_creation_disabled`. Dostępny pozostaje tryb lokalnego logowania
ChatGPT Business, a w CI można zamiast niego użyć subskrypcji Claude.

## GitHub Actions z subskrypcją Claude

1. Na swoim komputerze zainstaluj Claude Code i uruchom:

   ```bash
   claude setup-token
   ```

2. W przeglądarce zaloguj się do subskrypcji Claude **Pro, Max, Team lub Enterprise**
   i zatwierdź utworzenie tokena. Token pojawi się w terminalu; nie wklejaj go do kodu,
   rozmowy ani dokumentacji.
3. W obecnym repozytorium GitHub otwórz **Settings → Secrets and variables → Actions
   → New repository secret**.
4. **Name:** `CLAUDE_CODE_OAUTH_TOKEN`. **Secret:** token z `claude setup-token`.
   Zapisz przez **Add secret**.
5. Po wypchnięciu zmian workflow na `main` uruchom **Actions → update-context
   → Run workflow → main**. Workflow instaluje tylko CLI wybranego dostawcy:
   Claude Code `2.1.305` albo Codex `0.163.0`.

Zamiast subskrypcji możesz dodać sekret `ANTHROPIC_API_KEY` (klucz API z konsoli
Anthropic). Gdy są oba, workflow używa klucza API; token subskrypcji służy wtedy
jako zapas tylko przy braku klucza (nie ma automatycznego przełączenia po błędzie).
Do `CLAUDE_CODE_OAUTH_TOKEN` wklejaj wyłącznie token z `claude setup-token`
(`sk-ant-oat…`); klucz API wklejony tam kończy się błędem 401.

Bez klucza API nie potrzebujesz `ANTHROPIC_API_KEY`, tokena Codex ani instalowania aplikacji
Claude GitHub App: ten workflow wywołuje CLI bezpośrednio, a commit wykonuje
osobne zadanie z istniejącym `GITHUB_TOKEN`. Token Claude uwierzytelnia użycie
subskrypcji; obowiązują jej limity i ustawienia dodatkowego zużycia.

Źródła: [token subskrypcji Claude](https://code.claude.com/docs/en/authentication#generate-a-long-lived-token),
[Claude CLI w automatyzacji](https://code.claude.com/docs/en/headless).

Pierwsza generacja danego dostawcy jest pełną odbudową; następne pozostają
przyrostowe. Powrót do wcześniej używanego dostawcy wznawia jego własny stan,
bez ponownej pełnej analizy, jeśli źródła i instrukcja się nie zmieniły.
Wspólny prompt w `docs/context/instructions.md` otrzymuje nazwę faktycznie
wybranego generatora. Stan w katalogu tego dostawcy zapisuje pole `provider`.

CLI generatora obsługuje też jawny wybór lokalny z tokenem:

```bash
# Automatycznie: token Claude ma pierwszeństwo przed tokenem Codex.
python3 scripts/generate_application_context.py

# Jawny wybór, wymagający odpowiedniego tokena w środowisku.
python3 scripts/generate_application_context.py --provider claude
python3 scripts/generate_application_context.py --provider codex
```

## Szybki start lokalnie — bez tokena i bez klucza API

Wymagania: Python 3.12+, git i zainstalowany Codex CLI (sprawdzono 0.163.0).
Jeśli CLI nie jest zalogowany, uruchom `codex login` i wybierz konto ChatGPT
Business. `codex login status` powinien wskazać ChatGPT; w interaktywnej sesji
`codex` polecenie `/status` pozwala sprawdzić właściwy workspace Business.

Z katalogu repozytorium:

```bash
# Odśwież mapę, jeśli zmieniał się kod.
./scripts/update-context.sh

# Pełna pierwsza budowa, następnie aktualizacje przyrostowe.
python3 scripts/generate_application_context.py --auth chatgpt
```

Po zakończeniu przejrzyj opis i diff, następnie commituj
`docs/context/codex/application.md` wraz z `application-state.json` z tego samego
katalogu, plikami `stats.md`/`stats.json` oraz aktualną mapą. Nowy plik źródłowy najpierw dodaj
do git (`git add ścieżka`): generator analizuje tylko pliki śledzone. Treść bierze
z lokalnego drzewa roboczego, również przed commitem; stan zapisuje jej skróty
oraz bazowy commit HEAD.

Tryb lokalny używa istniejącego logowania CLI bez kopiowania `auth.json`.
Zmienne `OPENAI_API_KEY`, `CODEX_API_KEY` i `CODEX_ACCESS_TOKEN` nie są przekazywane
do lokalnego Codex. Nie zapisujemy poświadczeń w repozytorium. Własna konfiguracja
użytkownika nie jest ładowana; CLI używa domyślnego modelu i istniejącego magazynu
logowania. Użycie obciąża limity konta Business. Ten tryb jest blokowany w CI.

Podstawa: [`codex exec` korzysta z zapisanego logowania CLI](https://learn.chatgpt.com/docs/non-interactive-mode#authenticate-in-automation).

## Dokumenty i aktualizacja przyrostowa

Generator zapisuje w `docs/context/`:

- `repomap.md`: mechaniczna mapa klas i sygnatur;
- `instructions.md`: wspólna instrukcja wejściowa dla Codex i Claude;
- `codex/application.md` lub `claude/application.md`: opis architektury,
  przepływów, reguł i API, osobno dla każdego dostawcy;
- `codex/application-state.json` lub `claude/application-state.json`: skróty
  źródeł i commit bazowy ostatniego udanego generowania danego dostawcy,
  bez tokenów i treści plików.
- `codex/stats.md` i `claude/stats.md`: czytelny raport tokenów;
- `codex/stats.json` i `claude/stats.json`: historia prób generowania.

## Statystyki tokenów

Raport zawiera tokeny wejścia i wyjścia, sumę, odczyt i tworzenie cache,
reasoning (jeśli raportowany), czas, tryb pełny/przyrostowy, status oraz liczbę
analizowanych plików. JSON przechowuje także commit źródłowy i nazwy modeli,
o ile CLI je zwróciło; sama nazwa dostawcy Codex/Claude nie jest nazwą modelu.

Codex zwraca zużycie w zdarzeniach JSONL `turn.completed`; wejście obejmuje cache.
Claude zwraca zużycie w odpowiedzi JSON: sumujemy wejście bez cache, odczyt cache
i zapis cache, aby uzyskać porównywalne całkowite wejście. Reasoning jest częścią
wyjścia. Nie sumujemy podzbiorów ponownie i nie wyliczamy tokenów z długości tekstu.
Brak pola oznacza `null` w JSON i „brak danych” w raporcie, a nie zużycie zero.

`stats.json` ma pełną historię od wdrożenia pomiaru. `stats.md` pokazuje ostatnie
20 prób i sumę tokenów z prób z kompletnym pomiarem; wskazuje też liczbę prób bez
pełnych danych. Poprzednie generowania, które nie zapisywały telemetrii, nie są
odtwarzane ani szacowane. Raport nie zawiera transkryptu, promptu, źródeł ani tokenów
dostępowych. Zużycie tokenów nie jest kwotą faktury lub procentem limitu subskrypcji.

Próba zakończona błędem także trafia do lokalnej historii: mogła już zużyć tokeny.
W CI po błędzie statystyki można pobrać z artefaktu `application-context`, ale
zadanie zapisujące commit jest pomijane. Takie nieudane przebiegi nie dopiszą się
automatycznie do historii przechowywanej w repo; artefakt ma retencję 1 dzień.
Timeout lub błąd logowania może nie zwrócić żadnych danych o zużyciu.

Brak zmian nie uruchamia modelu i nie modyfikuje statystyk. Aby wykonać świadomy
pełny pomiar mimo braku zmian, użyj (zużywa limit subskrypcji):

```bash
python3 scripts/generate_application_context.py --auth chatgpt --provider codex --force
```

Źródła: [telemetria Codex](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable),
[liczniki cache Claude](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

Pierwszy przebieg analizuje wszystkie wybrane źródła. Kolejne porównują ich
SHA-256 z zapisanym stanem i wysyłają wyłącznie dodane/zmienione pliki, listę
usuniętych, aktualną mapę oraz poprzedni opis. Wybrany model aktualizuje dotknięte
fragmenty i powiązania, zachowując pozostały tekst. Wynik technicznie jest całym
dokumentem, więc model może wprowadzić również drobne różnice redakcyjne.
Brak zmian wejścia oznacza brak wywołania modelu. Porównanie obejmuje zmiany od
ostatniego **udanego** generowania, nawet gdy wcześniej workflow nie przeszedł.

Brak/uszkodzenie pliku stanu, ręczna zmiana opisu lub zmiana promptu powodują
pełną odbudowę dla wybranego dostawcy. Aby wymusić ją ręcznie, usuń
`application-state.json` z katalogu tego dostawcy, zacommituj
usunięcie i uruchom generator (lokalnie lub CI z tokenem). Nie usuwaj stanu przy zwykłych aktualizacjach.

## 1. Utwórz token Codex w ChatGPT Business

1. W ChatGPT przełącz się na właściwy workspace **Business**.
2. Właściciel workspace otwiera **Workspace settings → Permissions & roles**.
3. Włącz uprawnienia **Allow members to use Codex locally** (albo
   **Allow members to use Codex and Work Locally**) oraz **Allow members to use
   Codex access tokens** (w niektórych interfejsach **Allow users to create
   personal access tokens** w sekcji Access tokens).
4. Otwórz [**Access tokens**](https://chatgpt.com/admin/access-tokens) w panelu administracyjnym ChatGPT i wybierz **Create**.
5. Nazwij token np. `context-poc`. Jeśli pojawi się wybór zakresów, wybierz **Codex**.
6. Na POC ustaw krótki termin ważności, np. 7 dni. Utwórz token i skopiuj go.
   Nie będzie można ponownie wyświetlić jego wartości.

To token workspace Codex, a nie klucz z platform.openai.com, token GitHub ani
zawartość `~/.codex/auth.json`. Jeśli brak opcji Access tokens lub widzisz 403/404,
sprawdź workspace i uprawnienia z właścicielem; nie zastępuj tokena sesją przeglądarki.
Jeżeli ekran tworzenia tokena wymaga nowszego CLI, podnieś przypięte
`@openai/codex@0.163.0` w workflow do wskazanej wersji lub nowszej.

Źródło: [oficjalna dokumentacja tokenów Codex](https://learn.chatgpt.com/docs/enterprise/access-tokens).

## 2. Dodaj sekret w obecnym repozytorium GitHub

1. Repozytorium → **Settings → Secrets and variables → Actions**.
2. Wybierz **New repository secret**.
3. **Name:** `CODEX_ACCESS_TOKEN`.
4. **Secret:** wklej utworzony token Codex Business i kliknij **Add secret**.

Nie dodawaj go do Variables, pliku workflow, kodu ani commita. Nie wysyłaj tokena
w rozmowie. Nie jest potrzebny `OPENAI_API_KEY` ani dodatkowy token GitHub.
Token zużywa dostęp i limity przypisane do workspace; nie oznacza to
nielimitowanych ani gwarantowanie bezpłatnych przebiegów.

## 3. Włącz zapis i uruchom

1. **Settings → Actions → General → Workflow permissions**: umożliw zapis
   (**Read and write permissions**), jeśli polityka repo/organizacji tego wymaga.
   Sam workflow daje zapis wyłącznie zadaniu `commit`.
2. Gałąź `main` musi dopuszczać push od `GITHUB_TOKEN`; wymagany PR/review
   może blokować bezpośredni commit, tak jak w poprzedniej wersji POC.
3. Zacommituj i wypchnij przygotowane zmiany na `main`.
4. **Actions → update-context → Run workflow → Branch: main → Run workflow**.
   Zmiana workflow także sama wywoła przebieg po pushu na `main`.
5. Sprawdź zadania `update` i `commit`, następnie commit bota
   `chore(context): update repository map and application context`.
6. Wykonaj `git pull`. `AGENTS.md` kieruje przyszłe sesje Codex do obu dokumentów.
   Inne narzędzia wymagają własnej instrukcji odczytania tych plików.

Brak obu sekretów pomija instalację i uruchomienie AI; workflow aktualizuje samą
mapę, zachowując ostatni opis i stan. Podsumowanie informuje o pominięciu AI.
Błąd uwierzytelnienia przy obecnym sekrecie, limit,
timeout albo niepoprawny dokument zatrzymują zapis — poprzedni kontekst i stan
pozostają w repo. Przy nowszym commicie na `main` workflow nie rebazuje opisu
na zmieniony kod; należy uruchomić go ponownie dla aktualnego `main`.

## Zakres i ograniczenia POC

Wejście obejmuje śledzone pliki PHP w `src/`, `config/`, `public/`, `composer.json`
i `data/products.json`, z wykluczeniami z `scripts/repomap-exclude.txt`.
Testy, pliki lokalne, secrets i credentials są pomijane. Wykluczenie działa po
nazwie/ścieżce, nie jest skanerem sekretów: zwykły plik źródłowy także nie może
zawierać prawdziwych poświadczeń. Model otrzymuje treść dozwolonych źródeł.

Kod aplikacji nie jest wykonywany. Oba CLI dostają dane przez stdin i pracują w
pustym katalogu. Codex korzysta z sandboxa read-only; w CI ma osobny tymczasowy
CODEX_HOME, a lokalnie używa istniejącego magazynu logowania.
Claude ma osobny tymczasowy CLAUDE_CONFIG_DIR, wyłączone wszystkie narzędzia,
MCP i ładowanie ustawień użytkownika/projektu; nie używamy `--bare`, ponieważ
nie obsługuje tokenów subskrypcji OAuth. Odpowiedź Claude jest odczytywana z JSON
i musi mieć status sukcesu oraz prawidłowy dokument. Dany proces otrzymuje tylko
token swojego dostawcy, bez kluczy API i tokena konkurencyjnego dostawcy.
W CI token jest przekazywany tylko krokowi generowania (oraz sprawdzenia obecności),
po instalacji zależności. Nie publikujemy transkryptów ani pełnych błędów modelu.
Osobne zadanie zapisujące pobiera wyłącznie dokumenty kontekstu; nie otrzymuje tokenów AI.

Publiczne repo pozostaje publiczne; workflow działa tylko na `main` przez push
lub ręcznie, bez zdarzeń PR/forków. To uzgodniony kompromis POC. OpenAI zaleca
tokeny na zaufanych runnerach i ostrzega przed publicznym CI. Nie traktujemy tego
wariantu jako potwierdzonej konfiguracji produkcyjnej. Po POC unieważnij token
lub zastąp go tokenem z nową datą ważności w tym samym sekrecie GitHub.

Opis jest wynikiem modelu i wymaga weryfikacji w kodzie. Aktualizacja przyrostowa
może pominąć pośredni wpływ na niezmieniony moduł; pełna odbudowa służy też
okresowemu sprawdzeniu spójności. Zmiana samego ciała metody również wywoła
aktualizację, nawet jeśli mapa sygnatur pozostanie identyczna.

## Sprawdzenie lokalne bez tokena

```bash
python3 -m unittest discover -s tests -p 'test_application_context.py' -v
```

Testy korzystają z atrap obu CLI: sprawdzają pierwszeństwo Claude, wybór Codex,
brak tokenów, niezależne wyniki i stany dostawców, pełną budowę, aktualizację przyrostową,
usunięcia, brak wywołania przy braku zmian, filtrowanie źródeł i zachowanie stanu
przy błędzie, brak przełączenia na Codex po błędzie Claude oraz wybór lokalnego
logowania ChatGPT bez kluczy API (niezależnie od obecności tokena Claude).
Przebieg CI z tokenem trzeba sprawdzić po dodaniu sekretu. Lokalna komenda
`scripts/update-context.sh` nadal generuje samą mapę; opis generuje osobne
polecenie `python3 scripts/generate_application_context.py --auth chatgpt`.
