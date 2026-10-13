<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien być WYKLUCZONY (wzorzec *credentials*, wielkość liter bez znaczenia).

namespace App\Payment;

final class StripeCredentials
{
    public function apiKey(): string
    {
        return 'FAKE-DEMO-API-KEY-NOT-REAL';
    }
}
