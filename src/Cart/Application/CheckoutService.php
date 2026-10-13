<?php

declare(strict_types=1);

namespace App\Cart\Application;

use App\Cart\Domain\CartRepository;
use App\Cart\Domain\Exception\EmptyCart;
use App\Cart\Event\CartCheckedOut;
use App\Cart\Pricing\PricingCalculator;
use App\Order\Order;
use App\Order\OrderFactory;
use App\Shared\EventDispatcher;

/**
 * Złożenie zamówienia: waliduje koszyk, zamyka go, tworzy Order i publikuje zdarzenie CartCheckedOut
 * (na nie reagują m.in. rezerwacja stanu magazynu i logowanie).
 */
final class CheckoutService
{
    public function __construct(
        private readonly CartRepository $carts,
        private readonly PricingCalculator $pricing,
        private readonly OrderFactory $orders,
        private readonly EventDispatcher $events,
    ) {
    }

    public function checkout(string $cartId): Order
    {
        $cart = $this->carts->get($cartId);
        if ($cart->isEmpty()) {
            throw new EmptyCart('Cannot check out an empty cart');
        }

        $totals = $this->pricing->calculate($cart);
        $cart->markCheckedOut();
        $this->carts->save($cart);

        $order = $this->orders->fromCart($cart, $totals);
        $this->events->dispatch(new CartCheckedOut($cart, $order));

        return $order;
    }
}
