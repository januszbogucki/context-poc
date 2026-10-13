<?php

declare(strict_types=1);

namespace App\Cart\Application;

use App\Cart\Domain\Cart;
use App\Cart\Domain\CartRepository;
use App\Cart\Pricing\CartTotals;
use App\Cart\Pricing\InvalidPromoCode;
use App\Cart\Pricing\PricingCalculator;
use App\Cart\Pricing\PromoCodeRepository;
use App\Catalog\ProductRepository;

/**
 * Przypadki użycia koszyka (dodaj, zmień ilość, usuń, kod rabatowy). Każda metoda ładuje koszyk,
 * zmienia go przez agregat Cart i zapisuje.
 */
final class CartService
{
    public function __construct(
        private readonly CartRepository $carts,
        private readonly ProductRepository $products,
        private readonly PromoCodeRepository $promoCodes,
        private readonly PricingCalculator $pricing,
    ) {
    }

    public function show(string $cartId): Cart
    {
        return $this->carts->getOrCreate($cartId);
    }

    public function totals(Cart $cart): CartTotals
    {
        return $this->pricing->calculate($cart);
    }

    public function addItem(string $cartId, string $productId, int $quantity): Cart
    {
        $cart = $this->carts->getOrCreate($cartId);
        $cart->addProduct($this->products->get($productId), $quantity);
        $this->carts->save($cart);

        return $cart;
    }

    public function changeQuantity(string $cartId, string $productId, int $quantity): Cart
    {
        $cart = $this->carts->get($cartId);
        $cart->changeQuantity($this->products->get($productId), $quantity);
        $this->carts->save($cart);

        return $cart;
    }

    public function removeItem(string $cartId, string $productId): Cart
    {
        $cart = $this->carts->get($cartId);
        $cart->removeProduct($productId);
        $this->carts->save($cart);

        return $cart;
    }

    public function applyPromoCode(string $cartId, string $code): Cart
    {
        if ($this->promoCodes->find($code) === null) {
            throw InvalidPromoCode::withCode($code);
        }

        $cart = $this->carts->get($cartId);
        $cart->applyPromoCode(strtoupper($code));
        $this->carts->save($cart);

        return $cart;
    }
}
