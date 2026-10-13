<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Cart\Domain\Cart;
use App\Shared\Money;

/** Rabat procentowy z kodu rabatowego zapisanego w koszyku. */
final class PromoCodeDiscount implements DiscountPolicy
{
    public function __construct(private readonly PromoCodeRepository $promoCodes)
    {
    }

    public function discountFor(Cart $cart, Money $subtotal): Money
    {
        $code = $cart->promoCode();
        $promo = $code !== null ? $this->promoCodes->find($code) : null;

        return $promo !== null ? $subtotal->percent($promo->percent) : Money::zero();
    }
}
