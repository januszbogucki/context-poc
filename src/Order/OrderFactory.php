<?php

declare(strict_types=1);

namespace App\Order;

use App\Cart\Domain\Cart;
use App\Cart\Pricing\CartTotals;
use DateTimeImmutable;

/** Buduje zamówienie ze zamkniętego koszyka. Numer zamówienia ma format ORD-<8 znaków hex>. */
final class OrderFactory
{
    public function fromCart(Cart $cart, CartTotals $totals): Order
    {
        return new Order(
            'ORD-' . strtoupper(bin2hex(random_bytes(4))),
            $cart->id,
            $cart->items(),
            $totals,
            new DateTimeImmutable(),
        );
    }
}
