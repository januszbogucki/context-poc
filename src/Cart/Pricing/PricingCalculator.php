<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Cart\Domain\Cart;
use App\Shared\Money;

/**
 * Liczy sumy koszyka: wartość pozycji, rabaty (suma wszystkich DiscountPolicy, nie więcej niż wartość koszyka),
 * dostawa liczona od kwoty po rabatach. Każde nowe źródło rabatu to nowa klasa DiscountPolicy
 * dopisana w config/services.php.
 */
final class PricingCalculator
{
    /** @param list<DiscountPolicy> $discountPolicies */
    public function __construct(
        private readonly array $discountPolicies,
        private readonly ShippingCalculator $shipping,
    ) {
    }

    public function calculate(Cart $cart): CartTotals
    {
        $subtotal = $cart->subtotal();

        $discount = array_reduce(
            $this->discountPolicies,
            static fn (Money $sum, DiscountPolicy $policy) => $sum->add($policy->discountFor($cart, $subtotal)),
            Money::zero(),
        )->min($subtotal);

        $afterDiscount = $subtotal->subtract($discount);
        $shipping = $this->shipping->costFor($afterDiscount);

        return new CartTotals($subtotal, $discount, $shipping, $afterDiscount->add($shipping));
    }
}
