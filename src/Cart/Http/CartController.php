<?php

declare(strict_types=1);

namespace App\Cart\Http;

use App\Cart\Application\CartService;
use App\Cart\Application\CheckoutService;
use App\Cart\Domain\Cart;
use App\Cart\Domain\CartItem;
use App\Http\Request;
use App\Http\Response;

/**
 * Endpointy koszyka. Koszyk identyfikuje nagłówek X-Cart-Id; gdy go brak, generujemy nowy identyfikator
 * i zwracamy go w nagłówku odpowiedzi X-Cart-Id.
 */
final class CartController
{
    public function __construct(
        private readonly CartService $cart,
        private readonly CheckoutService $checkout,
    ) {
    }

    public function show(Request $request): Response
    {
        $cartId = $this->cartId($request);

        return $this->cartResponse($this->cart->show($cartId), 200, $cartId);
    }

    public function addItem(Request $request): Response
    {
        $cartId = $this->cartId($request);
        $cart = $this->cart->addItem(
            $cartId,
            (string) ($request->body['productId'] ?? ''),
            (int) ($request->body['quantity'] ?? 1),
        );

        return $this->cartResponse($cart, 201, $cartId);
    }

    public function changeQuantity(Request $request): Response
    {
        $cartId = $this->cartId($request);
        $cart = $this->cart->changeQuantity(
            $cartId,
            $request->attribute('productId'),
            (int) ($request->body['quantity'] ?? 0),
        );

        return $this->cartResponse($cart, 200, $cartId);
    }

    public function removeItem(Request $request): Response
    {
        $cartId = $this->cartId($request);

        return $this->cartResponse($this->cart->removeItem($cartId, $request->attribute('productId')), 200, $cartId);
    }

    public function applyPromo(Request $request): Response
    {
        $cartId = $this->cartId($request);
        $cart = $this->cart->applyPromoCode($cartId, (string) ($request->body['code'] ?? ''));

        return $this->cartResponse($cart, 200, $cartId);
    }

    public function checkout(Request $request): Response
    {
        $cartId = $this->cartId($request);

        return Response::json($this->checkout->checkout($cartId)->toArray(), 201, ['X-Cart-Id' => $cartId]);
    }

    private function cartId(Request $request): string
    {
        return $request->header('X-Cart-Id') ?? bin2hex(random_bytes(8));
    }

    private function cartResponse(Cart $cart, int $status, string $cartId): Response
    {
        return Response::json([
            'id' => $cart->id,
            'status' => $cart->status()->value,
            'promoCode' => $cart->promoCode(),
            'items' => array_map(static fn (CartItem $i) => $i->toArray(), $cart->items()),
            'totals' => $this->cart->totals($cart)->toArray(),
        ], $status, ['X-Cart-Id' => $cartId]);
    }
}
