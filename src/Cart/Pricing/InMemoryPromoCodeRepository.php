<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

/** Kody rabatowe zaszyte w kodzie (PoC). Wielkość liter nie ma znaczenia. */
final class InMemoryPromoCodeRepository implements PromoCodeRepository
{
    /** @var array<string, PromoCode> */
    private array $codes;

    public function __construct()
    {
        $this->codes = [
            'WELCOME10' => new PromoCode('WELCOME10', 10),
            'SUMMER20' => new PromoCode('SUMMER20', 20),
        ];
    }

    public function find(string $code): ?PromoCode
    {
        return $this->codes[strtoupper($code)] ?? null;
    }
}
