<?php

declare(strict_types=1);

// FIXTURE do testu wykluczeń mapy repozytorium. Dane są wymyślone, to nie są prawdziwe poświadczenia.
// Powinien ZOSTAĆ w mapie (zwykły plik, nic nie pasuje do wzorców).

namespace App\Payment;

interface PaymentGateway
{
    public function charge(int $amountInGrosze, string $currency): bool;
}
