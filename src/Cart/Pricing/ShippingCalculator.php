<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Shared\Money;

/** Dostawa kosztuje 15,00 PLN, a od 200,00 PLN (po rabatach) jest darmowa. */
final class ShippingCalculator
{
    private const FREE_FROM_GROSZE = 20_000;
    private const FLAT_RATE_GROSZE = 1_500;

    public function costFor(Money $amountAfterDiscounts): Money
    {
        if ($amountAfterDiscounts->amount === 0) {
            return Money::zero();
        }

        return $amountAfterDiscounts->isGreaterThanOrEqual(new Money(self::FREE_FROM_GROSZE))
            ? Money::zero()
            : new Money(self::FLAT_RATE_GROSZE);
    }
}
