<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien być WYKLUCZONY (wzorzec *secret*).

namespace App\Auth;

final class SecretLoader
{
    public function load(string $name): string
    {
        return 'FAKE-DEMO-SECRET-NOT-REAL';
    }
}
