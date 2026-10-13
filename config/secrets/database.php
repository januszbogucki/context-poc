<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien być WYKLUCZONY (wzorzec config/secrets/*).

namespace App\Config;

final class DatabaseConnectionSettings
{
    private const PASSWORD = 'FAKE-DEMO-PASSWORD-NOT-REAL';

    public function password(): string
    {
        return self::PASSWORD;
    }
}
