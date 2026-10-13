<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Cart\Domain\Cart;
use App\Shared\Money;

interface DiscountPolicy
{
    /** Zwraca kwotę rabatu (zero, jeśli reguła nie ma zastosowania). */
    public function discountFor(Cart $cart, Money $subtotal): Money;
}
