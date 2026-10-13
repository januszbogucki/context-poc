<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien być WYKLUCZONY (wzorzec *.local.php).

function localOverrides(): array
{
    return ['debug' => true, 'dsn' => 'mysql://demo:FAKE-DEMO@localhost/shop'];
}
