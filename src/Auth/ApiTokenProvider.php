<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien ZOSTAĆ w mapie: słowo "token" nie jest w żadnym wzorcu. To pokazuje GRANICĘ wykluczeń:
// filtr działa po nazwach plików, więc tego, czego nie przewidzieliśmy we wzorcach, nie złapie.

namespace App\Auth;

final class ApiTokenProvider
{
    public function token(): string
    {
        return 'FAKE-DEMO-TOKEN-NOT-REAL';
    }
}
