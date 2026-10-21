# Statystyki generowania kontekstu — Claude

Pomiar z telemetrii CLI. Historia obejmuje tylko przebiegi od włączenia pomiaru.
Zużycie tokenów nie jest kwotą rachunku ani procentem limitu subskrypcji.

- Próby generowania: 1.
- Zakończone sukcesem: 1.
- Próby z pełnym pomiarem: 1; bez pełnych danych: 0.
- Suma tokenów w próbach z pełnym pomiarem: **39 020**.

## Ostatnie przebiegi (maksymalnie 20)

| Czas UTC | Status | Tryb | Pliki analizowane | Wejście | Wyjście | Razem | Cache odczyt | Cache zapis | Reasoning | Czas (s) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-21T07:19:12+00:00 | success | full | 49 | 26269 | 12751 | 39020 | 649 | 25618 | 3554 | 112.421 |

## Jak czytać liczby

Wejście obejmuje także cache. Cache odczyt/zapis to części wejścia; nie dodawaj ich drugi raz.
Reasoning, jeśli CLI go raportuje, jest częścią wyjścia; nie doliczaj go do sumy.
Wejście + wyjście = razem. Brak danych oznacza brak pomiaru, a nie zero tokenów.
Sumy obejmują również nieudane próby, jeśli CLI zwróciło dla nich pełne dane.
Przebieg bez zmian źródeł nie uruchamia modelu i nie dopisuje statystyk.
Pełna historia, commit źródłowy i nazwy modeli (o ile CLI je zwróciło) są w `stats.json`.
