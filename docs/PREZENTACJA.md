# Plan prezentacji: RepoMapper i automatyczne odświeżanie kontekstu

> Historyczna prezentacja wariantu bez modelu. Workflow rozszerzono o pełną
> pierwszą budowę i kolejne przyrostowe aktualizacje przez Codex Business.
> Logowanie lokalne i opcjonalny token CI: [CONTEXT-SETUP.md](CONTEXT-SETUP.md).

Gildia backendowa, 14.10.2026, 15 minut. Komendy, kod do demo na żywo i plan B są w [`DEMO.md`](DEMO.md). Ten plik opisuje, **co powiedzieć i w jakiej kolejności**.

## Plan w skrócie

| Część | Czas | O czym |
|---|---|---|
| 1. Czym jest RepoMapper | 2 min | Problem, który rozwiązuje, i czym jest „kontekst” |
| 2. Instalacja i wymagania | 2 min | Co trzeba mieć, licencja |
| 3. Jak go używać | 2 min | Jedna komenda lokalnie |
| 4. Co naprawdę robi | 3 min | Od kodu PHP do pliku z mapą |
| 5. Co dzieje się przy merge do `main` | 4 min | Action, demo na żywo |
| 6. Wyniki, ograniczenia, wdrożenie w firmie | 2 min | Uczciwe podsumowanie |

## 1. Czym jest RepoMapper

**Problem.** Claude nie zna Twojego repo. Przy każdym pytaniu sam szuka plików (grep), otwiera je i czyta. Każdy otwarty plik to tokeny (koszt, czas) i kolejna tura rozmowy.

**Kontekst** to wiedza o projekcie podana z góry, zanim Claude zacznie szukać. Technicznie to zwykły tekst doklejony do rozmowy.

**RepoMapper** to małe narzędzie open source (Python), które z kodu źródłowego buduje **mapę repozytorium**: dla każdego pliku nazwy klas i sygnatury metod z numerami linii.

- Autor: Pete Davis, licencja MIT, repo `github.com/pdavis68/RepoMapper`.
- Powstał na wzór mapy repozytorium znanej z narzędzia aider (autor deklaruje, że kod jest napisany od nowa).
- Działa lokalnie i **nie używa modelu AI**. To czyste parsowanie kodu.
- Ma tryb CLI oraz serwer MCP (nasza wersja używa własnego skryptu, patrz punkt 3).

**Fragment mapy** (z naszego projektu):

```
src/Cart/Pricing/ShippingCalculator.php:
  10: final class ShippingCalculator
  15:     public function costFor(Money $amountAfterDiscounts): Money
```

## 2. Instalacja i wymagania

| Wymaganie | Wartość |
|---|---|
| Język | Python 3.12 (sprawdzone na 3.12.3) |
| Narzędzia | `git`, `pip` |
| Docker | nie potrzeba |
| Lokalny model | nie potrzeba |
| Klucz API / konto | nie potrzeba (narzędzie nie wywołuje modelu) |
| Sieć | pobranie kodu z GitHuba, pakietów z PyPI, słownika tokenizatora (`tiktoken`) |
| Licencja | MIT (użycie komercyjne dozwolone, bez opłat) |

**Instalacja u nas** to jedna komenda, `./scripts/update-context.sh`, która sama: pobiera RepoMappera w przypiętej wersji (commit `3ef8914`), tworzy osobne środowisko Pythona (`.context-tools/`, ignorowane przez git) i instaluje zależności.

**Uwaga, która kosztowała nas czas:** zależności trzeba przypiąć. `requirements.txt` autora nie przypina wersji i pip instaluje nowszy `tree-sitter` (0.26), w którym zniknęła metoda `Language.query`. Wtedy wszystkie pliki PHP kończą błędem. Wersje z `uv.lock` autora działają (`tree-sitter 0.25.1` i pozostałe w `scripts/repomap-requirements.txt`).

**Licencje zależności** (sprawdzone w metadanych pakietów): MIT, BSD, Apache-2.0. Niesprawdzone: licencje gramatyk w `tree-sitter-language-pack`, plik słownika tokenizatora i zależności zależności. Przy wdrożeniu w firmie licencje powinien potwierdzić dział prawny.

## 3. Jak go używać

Lokalnie, jedna komenda z katalogu repo:

```bash
./scripts/update-context.sh
```

Wynik: `docs/context/repomap.md`. Pierwsze uruchomienie pobiera narzędzie, kolejne trwają kilka sekund (u nas ok. 12 s).

Dlaczego własny skrypt, a nie CLI autora: w użytej wersji RepoMappera CLI drukuje wynik jako krotkę Pythona (tekst plus raport) zamiast czystego tekstu, więc nie nadaje się do zapisu w pliku. Skrypt `scripts/generate_repomap.py` woła klasę `RepoMap` bezpośrednio, sortuje bloki po nazwie pliku (żeby wynik był powtarzalny) i pomija linie rankingu, które i tak są identyczne.

**Czego to nie robi:** Claude Code **nie czyta tego pliku automatycznie**, czyta tylko `CLAUDE.md`. Żeby mapa trafiała do rozmowy, trzeba ją podpiąć (linia w `CLAUDE.md`, hook albo MCP). To jest otwarta decyzja zespołu. W teście porównawczym dokleiłem mapę do promptu systemowego.

## 4. Co narzędzie naprawdę robi

Cały proces jest mechaniczny:

1. **Wybiera pliki** (u nas: pliki PHP śledzone przez git, czyli bez `vendor/` i `var/`).
2. **Parsuje je biblioteką tree-sitter.** To parser składni, rozumie strukturę języka, nie jest to zwykłe wyszukiwanie tekstu. Wyciąga **definicje** (klasy, metody) i **odwołania** do nich.
3. **Buduje graf** zależności: pliki to węzły, odwołania to krawędzie.
4. **Rankinguje algorytmem PageRank** (jak w wyszukiwarce): ważniejsze są pliki, do których inne często się odwołują. U nas wszystkie pliki dostały tę samą wartość, więc ranking niewiele wnosi, a ja sortuję po nazwie.
5. **Mieści wynik w limicie tokenów** (u nas 4096) i zapisuje jako tekst.

W wyniku nie ma ani jednej informacji „zrozumianej” przez AI. To odcisk struktury kodu.

### Co mapa zawiera, a czego nie

| Zawiera | Nie zawiera |
|---|---|
| Klasy, metody, sygnatury, numery linii | Powiązań (kto kogo wywołuje) |
| | Wiringu: `config/routes.php`, `config/services.php`, `public/index.php` (nie mają klas ani funkcji) |
| | Enumów PHP (brakuje `CartStatus`) |
| | Reguł biznesowych (np. progu darmowej dostawy 200 zł) |

### Czym jest „kontekst” (warstwy)

Nasz PoC pokrywa **tylko pierwszą warstwę**:

1. **Struktura kodu** (klasy, sygnatury): RepoMapper, deterministycznie i tanio.
2. **Powiązania** (kto kogo używa, wiring): indeks symboli (np. Serena) albo opis pisany przez model.
3. **Architektura i konwencje:** człowiek albo model, zwykle `CLAUDE.md`.
4. **Reguły biznesowe:** człowiek albo model.
5. **Jak pracować z repo** (uruchomienie, testy).
6. **Model danych i API.**
7. **Decyzje i historia** (dlaczego tak zrobiono): tylko człowiek.
8. **Dokumentacja bibliotek zewnętrznych:** usługa chmurowa (Context7), u nas odpada.

Warstw 2–4 nie wygeneruje RepoMapper. Można je zlecić modelowi promptem (np. `claude -p "..."`), ale to oznacza koszt, wynik niepowtarzalny, konieczność przeglądu i uwierzytelnienie Claude'a w CI. Tego wariantu **nie badaliśmy**.

## 5. Co dzieje się przy merge do `main`

W PoC feature branch trafia do `main`. W firmie docelowo będzie to merge `develop → master` (wydania co kilka do kilkunastu dni).

```
1. Merge PR do main (zmiana w src/, config/, public/ lub scripts/)
2. GitHub widzi push i uruchamia workflow "update-context"
3. Runner (tymczasowa maszyna ubuntu-24.04) pobiera repo
4. Instaluje Pythona, pobiera RepoMappera w przypiętej wersji, instaluje zależności
5. ./scripts/update-context.sh generuje docs/context/repomap.md
6. Jeśli mapa się nie zmieniła: koniec ("Kontekst bez zmian")
7. Jeśli się zmieniła: bot github-actions[bot] commituje plik bezpośrednio na main
8. Każdy po git pull ma świeży plik
```

**Dowód z PoC:** po merge PR #1 workflow uruchomił się sam, trwał 24 s i dopisał na `main` commit `chore(context): update repository map` (`ff10df1`), 21 s po merge. Plik ma 10 338 bajtów.

**Co widać w zakładce Actions:** zwijane sekcje `1/3 Pobieranie narzędzia`, `2/3 Instalacja zależności`, `3/3 Generowanie mapy` oraz tabelka z podsumowaniem (gałąź, commit, plik, kto wywołał). Przy braku zmian: „Kontekst bez zmian”.

**Dlaczego nie ma pętli:** commit bota zmienia tylko `docs/context/`, a filtr uruchamia workflow tylko dla `src/**`, `config/**`, `public/**`, `scripts/**` i samego pliku workflow. Poza tym push z wbudowanego `GITHUB_TOKEN` sam nie uruchamia kolejnych workflow.

**Koszt tego kroku:** zero tokenów i zero kluczy API (używamy tylko wbudowanego `GITHUB_TOKEN`). Zużywa minuty GitHub Actions. Dla publicznego repo standardowe runnery są darmowe. Dla prywatnego repo na koncie Free jest 2000 minut miesięcznie, a jeden przebieg to ok. 25 s. Pule firmowe trzeba sprawdzić w ustawieniach organizacji.

**Dlaczego commit prosto na `main`, a nie PR:** dla mechanicznej, powtarzalnej mapy nie ma czego recenzować, a PR-y po każdym merge byłyby szumem. Wadą jest to, że działa tylko bez ochrony gałęzi wymagającej PR i review. Dla kontekstu pisanego przez model PR miałby sens.

## 6. Wyniki, ograniczenia, wdrożenie w firmie

### Test porównawczy (5 pytań, jedno uruchomienie każdego)

A: repo bez kontekstu. B: to samo repo plus mapa dołożona do promptu systemowego.

| | A bez kontekstu | B z mapą |
|---|---|---|
| Poprawność (max 10, oceniałem sam) | 8 | 9 |
| Tury | 26 | 19 |
| Wywołania narzędzi | 21 | 14 |
| Otwarte pliki | 14 | 10 |
| Czas | 47 s | 44 s |
| Koszt | 0,30 USD | 0,30 USD |

**Wniosek:** mapa skraca drogę do odpowiedzi (ok. jedną trzecią mniej kroków), ale nie obniża kosztu, bo dokłada ok. 4 tys. tokenów do każdego zapytania. Jakość jest porównywalna.

**Ograniczenia testu:** tylko 5 pytań i jedno uruchomienie każdego (odpowiedzi modelu nie są deterministyczne), mały projekt (46 plików), pytania i kod ułożyłem sam, ocenę wystawiłem sam. W jednym przebiegu wariantu A Claude zajrzał do innej kopii repo z mapą, więc ten wynik odrzuciłem i użyłem czystej powtórki. Hipoteza do sprawdzenia: korzyść rośnie z wielkością repo.

### Kryteria oceny (moje własne, nieuzgodnione z zespołem)

| Kryterium | RepoMapper w tym PoC |
|---|---|
| Jakość | Niewielki wpływ w małym repo. Tylko struktura, bez powiązań i reguł. |
| Koszt (tokeny i czas) | Budowanie: 0 tokenów, ok. 25 s w CI. Użycie: +ok. 4 tys. tokenów na zapytanie, w teście koszt całkowity bez zmian. |
| Wysiłek | Niski: jedna komenda i jeden plik workflow. Wymaga przypięcia wersji. |
| Aktualność | Dobra: odświeżana automatycznie po merge, maksymalnie nieświeża o kilkanaście dni między wydaniami. |
| Wymagania | Python 3.12, git, dostęp do internetu w CI. Bez Dockera i bez modelu. |
| Bezpieczeństwo | Kod uruchamiany lokalnie, nic z kodu nie wysyłane do narzędzia. Cudzy kod w CI (przypięty commit, przejrzany, brak połączeń sieciowych poza tokenizatorem). Projekt jednej osoby. |

### Co potrzeba, żeby wdrożyć to w firmowym repo

- **Ochrona gałęzi `master`:** bot commituje bezpośrednio, więc reguła wymagająca PR i review go zablokuje. Potrzebny wyjątek dla bota albo wariant z PR (zmiana w workflow to kilka linii).
- **Uprawnienia workflow:** w repo musi być włączone „Read and write permissions” dla `GITHUB_TOKEN`.
- **Runner:** na standardowych runnerach GitHuba działa. Przy własnych (self-hosted) za firewallem trzeba otworzyć `github.com`, PyPI i serwer tokenizatora albo użyć lustra pakietów.
- **Zgoda na uruchamianie cudzego kodu w CI** i powtórzenie przeglądu bezpieczeństwa w firmie.
- **Utrzymanie:** podnoszenie wersji akcji (`checkout@v7`, `setup-python@v7`, runner `ubuntu-24.04`) i samego narzędzia.
- **Decyzja:** jak Claude Code ma korzystać z mapy (dziś jej nie czyta) oraz czy commit bota na `master` jest akceptowalny.
- **Pule minut Actions** w firmowym planie GitHub (nieznane, do sprawdzenia w ustawieniach organizacji).

### Kierunek rozwoju (jedno zdanie)

Podejście hybrydowe: mapa deterministyczna dla warstwy struktury, a opcjonalnie model piszący architekturę i reguły przez prompt, ale tylko przez PR z review. Tego wariantu nie badaliśmy.
