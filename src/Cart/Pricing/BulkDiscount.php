<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Cart\Domain\Cart;
use App\Shared\Money;

/** Automatyczny rabat 5% dla koszyków o wartości co najmniej 500,00 PLN. Sumuje się z kodem rabatowym. */
final class BulkDiscount implements DiscountPolicy
{
    private const THRESHOLD_GROSZE = 50_000;
    private const PERCENT = 5;

    public function discountFor(Cart $cart, Money $subtotal): Money
    {
        return $subtotal->isGreaterThanOrEqual(new Money(self::THRESHOLD_GROSZE, $subtotal->currency))
            ? $subtotal->percent(self::PERCENT)
            : Money::zero();
    }
}
