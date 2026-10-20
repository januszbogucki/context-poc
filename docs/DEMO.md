# Ściągawka do demo: automatyczny kontekst repozytorium (RepoMapper + GitHub Action)

> Poniższy scenariusz opisuje historyczny wariant z samą mapą. Aktualny workflow
> dodaje przyrostowe generowanie opisu przez Codex Business (lokalnie przez
> logowanie ChatGPT; w CI opcjonalnie przez token).
> Konfiguracja i aktualne zachowanie: [CONTEXT-SETUP.md](CONTEXT-SETUP.md).

Demo na gildii backendowej, 14.10.2026, 15 minut. Dwa przypadki:
1. porównanie promptów z kontekstem i bez,
2. GitHub Action, który buduje i odświeża kontekst po merge.

> Uwaga: ten plik leży w `docs/`, a bot zapisuje tylko w `docs/context/`. Zmiana tego pliku nie uruchamia Action.

## Przed demo (zrób dzień wcześniej)

- [ ] `main` jest zielony w zakładce Actions, a `docs/context/repomap.md` jest na `main` (commit od `github-actions[bot]`).
- [ ] **Przygotuj gałąź ze zmianą do demo i wypchnij ją PRZED prezentacją** (kod niżej). Na żywo otwierasz tylko PR i klikasz merge w przeglądarce, więc nie wpisujesz tokenu przy ludziach.
- [ ] Lokalnie `git pull` na `main` i uruchomiony skrypt raz (żeby `.context-tools/` było pobrane i demo lokalne trwało kilka sekund).
- [ ] Zrzut ekranu ostatniego zielonego przebiegu (plan B, gdyby GitHub albo sieć zawiodły).
- [ ] Token do GitHuba nie jest nigdzie wklejony w terminalu ani w historii.

## Scenariusz (15 min)

| Min | Co pokazujesz | Co mówisz |
|---|---|---|
| 0–1 | Repo: mini sklep w czystym PHP (`src/Cart`, `src/Catalog`, `config/`) | Claude za każdym razem odkrywa strukturę kodu od zera. Kontekst ma to skrócić. |
| 1–3 | `scripts/repomap-requirements.txt`, README RepoMappera | Narzędzie: mapa klas i sygnatur metod (tree-sitter + ranking). Licencja MIT. Python 3.12, bez Dockera i bez lokalnego modelu. Wersje przypięte. |
| 3–5 | Lokalnie `./scripts/update-context.sh`, potem `docs/context/repomap.md` | Start ręczny: jedna komenda, ok. 12 s. Wynik to zwykły plik tekstowy w repo. |
| 5–7 | `.github/workflows/update-context.yml` | Co triggeruje: push na `main` ze zmianą w kodzie (albo ręcznie). Bot commituje mapę. Zero sekretów poza wbudowanym `GITHUB_TOKEN`, zero kosztów API. |
| 7–11 | **Na żywo:** PR z gotową zmianą → merge → zakładka Actions → commit bota | Kontekst odświeża się sam po merge. Rozwiń sekcje 1/3, 2/3, 3/3 w logu, pokaż tabelkę podsumowania. |
| 11–13 | Wyniki testu A/B (tabela niżej) | Mapa skraca drogę do odpowiedzi, ale nie obniża kosztu. Wynik wstępny. |
| 13–15 | Ograniczenia i „co potrzeba w firmie” | Patrz ostatnie sekcje. Pytania. |

## Komendy

```bash
# Odświeżenie kontekstu lokalnie
./scripts/update-context.sh

# Podgląd wyniku
head -40 docs/context/repomap.md

# Co zmienił bot
git pull && git log --oneline -5 --format='%h %an %s'
```

## Zmiana do demo na żywo (nowy rodzaj rabatu)

Gałąź przygotuj wcześniej (np. `demo-rabat`). Dwa pliki.

**1. Nowy plik `src/Cart/Pricing/ThresholdDiscount.php`:**

```php
<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Cart\Domain\Cart;
use App\Shared\Money;

/** Rabat 50,00 PLN dla koszyków o wartości co najmniej 300,00 PLN. Sumuje się z pozostałymi rabatami. */
final class ThresholdDiscount implements DiscountPolicy
{
    private const THRESHOLD_GROSZE = 30_000;
    private const AMOUNT_GROSZE = 5_000;

    public function discountFor(Cart $cart, Money $subtotal): Money
    {
        return $subtotal->isGreaterThanOrEqual(new Money(self::THRESHOLD_GROSZE, $subtotal->currency))
            ? new Money(self::AMOUNT_GROSZE, $subtotal->currency)
            : Money::zero();
    }
}
```

**2. `config/services.php`:** dodaj `use App\Cart\Pricing\ThresholdDiscount;` obok pozostałych `use` oraz `new ThresholdDiscount(),` w tablicy polityk w `PricingCalculator`, po `new BulkDiscount(),`.

Sprawdzone: koszyk 358 zł dostaje rabat 50 zł, koszyk 299 zł nie dostaje nic, `php tests/run.php` przechodzi.

Po merge w `docs/context/repomap.md` pojawi się nowy blok z klasą `ThresholdDiscount`. Warto to pokazać w diffie commita bota.

## Wyniki testu A/B (pytania 1 do 5, jedno uruchomienie każdego)

A: repo bez kontekstu. B: to samo repo plus mapa dołożona do promptu systemowego.

| | A bez kontekstu | B z mapą |
|---|---|---|
| Poprawność (max 10, oceniałem sam) | 8 | 9 |
| Tury | 26 | 19 |
| Wywołania narzędzi | 21 | 14 |
| Otwarte pliki | 14 | 10 |
| Czas | 47 s | 44 s |
| Koszt | 0,30 USD | 0,30 USD |

Wniosek: mapa skraca drogę do odpowiedzi (ok. jedną trzecią mniej kroków), ale nie obniża kosztu, bo dokłada ok. 4 tys. tokenów do każdego zapytania. Jakość porównywalna.

**Ograniczenia (powiedz wprost):**
- 5 pytań, jedno uruchomienie, odpowiedzi modelu nie są deterministyczne. To tendencja, nie dowód.
- Mały projekt (46 plików), a pytania i kod ułożyłem sam.
- W jednym przebiegu wariantu A Claude zajrzał do innej kopii repo z mapą. Ten wynik odrzuciłem i użyłem czystej powtórki.
- W jednym pytaniu z mapą Claude odpowiedział bez otwarcia żadnego pliku (zastrzegł, że nie zweryfikował reguły). Mapa daje strukturę, nie reguły biznesowe.
- Hipoteza do sprawdzenia: korzyść rośnie z wielkością repo.

## Ograniczenia samej mapy

- Nie widzi wiringu: `config/routes.php`, `config/services.php` i `public/index.php` nie mają klas ani funkcji, więc w mapie ich nie ma.
- Nie rozpoznaje enumów PHP (brakuje `CartStatus`).
- Nie pokazuje powiązań między klasami ani reguł biznesowych (np. progu darmowej dostawy).
- Ranking jest płaski: wszystkie pliki mają tę samą wartość, więc mapa jest sortowana po nazwie pliku.
- Claude Code **nie czyta tej mapy automatycznie**. Czyta `CLAUDE.md`. Podpięcie mapy (linia w `CLAUDE.md`, hook albo MCP) to osobna, otwarta decyzja.

## Licencja i wymagania (to mów ustnie, demo tego nie pokazuje)

- RepoMapper: **MIT** (użycie komercyjne dozwolone, bez opłat, zachowanie noty o prawach autorskich przy dystrybucji kodu).
- Zależności (tree-sitter, tiktoken, networkx, diskcache, grep-ast, pygments, tree-sitter-language-pack): MIT, BSD, Apache-2.0. Nie sprawdzałem licencji gramatyk w `tree-sitter-language-pack`, plików słownika tokenizatora ani zależności zależności.
- Python 3.12, `pip`, `git`. Bez Dockera i bez lokalnego modelu. Wersje przypięte do `uv.lock` autora, bo bez przypięcia nowe `tree-sitter` (0.26) łamie parsowanie.
- Narzędzie nie wywołuje modelu ani żadnej usługi. Jedyne połączenia sieciowe to pobranie kodu z GitHuba, pakietów z PyPI i słownika tokenizatora (`tiktoken`).
- Projekt jednej osoby, bez gwarancji wsparcia. Zrobiony w oparciu o repo-mapę aidera (Apache-2.0), autor deklaruje, że nie dzieli z nim kodu (nie weryfikowałem).
- To nie jest porada prawna, licencje powinien potwierdzić dział prawny.

## Co może triggerować odświeżenie kontekstu

- **Zrobione:** skrypt lokalnie (start) i GitHub Action po push na `main` (w firmie `master`) ze zmianą w kodzie, plus ręczne uruchomienie.
- **Nie robione, wspomnieć ustnie:** hook `SessionStart` (mapa liczona lokalnie przy starcie sesji, bez commitów), watcher plików.

## Co potrzeba, żeby wdrożyć to w firmowym repo

- **Ochrona gałęzi `master`.** Bot commituje bezpośrednio, więc reguła wymagająca PR i review go zablokuje. Trzeba wyjątku dla bota albo wariantu z PR (zmiana w workflow to kilka linii).
- **Uprawnienia workflow:** w repo musi być włączone „Read and write permissions” dla `GITHUB_TOKEN`.
- **Runner:** na standardowych runnerach GitHuba działa. Przy własnych (self-hosted) za firewallem trzeba otworzyć `github.com`, PyPI i serwer tokenizatora albo użyć lustra pakietów.
- **Zgoda na uruchamianie cudzego kodu w CI.** Ograniczamy ryzyko przypięciem commita i wersji pakietów oraz przeglądem kodu (brak połączeń sieciowych poza tokenizatorem), ale przegląd warto powtórzyć w firmie.
- **Utrzymanie:** podnoszenie wersji akcji (obecnie `checkout@v7`, `setup-python@v7`, runner `ubuntu-24.04`) i samego narzędzia.
- **Koszt:** w tej wersji brak kosztów API. Zużywa tylko minuty Actions (kilkadziesiąt sekund na przebieg).
- **Decyzja produktowa:** jak Claude Code ma korzystać z mapy oraz czy commit bota na `master` jest akceptowalny, czy zespół woli PR.

## Plan B, gdy coś nie zadziała na żywo

- Brak sieci albo GitHub nie reaguje: pokaż zrzut ostatniego zielonego przebiegu i commit bota w historii `main`.
- Przebieg czerwony: kliknij krok z błędem w logu i pokaż, że widać dokładnie, co się wywaliło (to też argument za Actions).
- Action nie wystartował: sprawdź, czy merge poszedł do `main` i czy zmiana dotyka plików z listy `paths` w workflow (`src/**`, `config/**`, `public/**`, `scripts/**`). Zawsze możesz uruchomić go ręcznie przyciskiem **Run workflow** w zakładce Actions.
