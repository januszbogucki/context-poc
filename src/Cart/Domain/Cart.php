<?php

declare(strict_types=1);

namespace App\Cart\Domain;

use App\Cart\Domain\Exception\CartAlreadyCheckedOut;
use App\Cart\Domain\Exception\InsufficientStock;
use App\Cart\Domain\Exception\InvalidQuantity;
use App\Catalog\Product;
use App\Shared\Money;

/**
 * Agregat koszyka. Pilnuje reguł: ilość >= 1, ilość nie większa niż stan magazynu,
 * brak zmian po złożeniu zamówienia. Nie zna cen promocyjnych ani kosztów dostawy (to robi Pricing).
 */
final class Cart
{
    /** @var array<string, CartItem> klucz: productId */
    private array $items = [];

    private ?string $promoCode = null;

    private CartStatus $status = CartStatus::Open;

    public function __construct(public readonly string $id)
    {
    }

    public function addProduct(Product $product, int $quantity): void
    {
        $this->assertOpen();
        $this->assertQuantity($quantity);

        $newQuantity = ($this->items[$product->id]->quantity ?? 0) + $quantity;
        $this->assertInStock($product, $newQuantity);

        $this->items[$product->id] = new CartItem($product->id, $product->name, $product->price, $newQuantity);
    }

    public function changeQuantity(Product $product, int $quantity): void
    {
        $this->assertOpen();
        $this->assertQuantity($quantity);
        $this->assertInStock($product, $quantity);

        $item = $this->items[$product->id] ?? throw new InvalidQuantity("Product {$product->id} is not in the cart");
        $this->items[$product->id] = $item->withQuantity($quantity);
    }

    public function removeProduct(string $productId): void
    {
        $this->assertOpen();
        unset($this->items[$productId]);
    }

    public function applyPromoCode(string $code): void
    {
        $this->assertOpen();
        $this->promoCode = $code;
    }

    public function markCheckedOut(): void
    {
        $this->assertOpen();
        $this->status = CartStatus::CheckedOut;
    }

    /** @return list<CartItem> */
    public function items(): array
    {
        return array_values($this->items);
    }

    public function isEmpty(): bool
    {
        return $this->items === [];
    }

    public function promoCode(): ?string
    {
        return $this->promoCode;
    }

    public function status(): CartStatus
    {
        return $this->status;
    }

    public function subtotal(): Money
    {
        return array_reduce(
            $this->items,
            static fn (Money $sum, CartItem $item) => $sum->add($item->lineTotal()),
            Money::zero(),
        );
    }

    /**
     * Odtworzenie koszyka z zapisanych danych (używa FileCartRepository). Pomija reguły biznesowe.
     *
     * @param list<CartItem> $items
     */
    public static function restore(string $id, array $items, ?string $promoCode, CartStatus $status): self
    {
        $cart = new self($id);
        foreach ($items as $item) {
            $cart->items[$item->productId] = $item;
        }
        $cart->promoCode = $promoCode;
        $cart->status = $status;

        return $cart;
    }

    private function assertOpen(): void
    {
        if ($this->status !== CartStatus::Open) {
            throw new CartAlreadyCheckedOut("Cart {$this->id} is already checked out");
        }
    }

    private function assertQuantity(int $quantity): void
    {
        if ($quantity < 1) {
            throw new InvalidQuantity('Quantity must be at least 1');
        }
    }

    private function assertInStock(Product $product, int $quantity): void
    {
        if ($quantity > $product->stock) {
            throw new InsufficientStock("Only {$product->stock} of {$product->id} in stock");
        }
    }
}
