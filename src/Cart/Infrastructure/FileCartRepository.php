<?php

declare(strict_types=1);

namespace App\Cart\Infrastructure;

use App\Cart\Domain\Cart;
use App\Cart\Domain\CartItem;
use App\Cart\Domain\CartRepository;
use App\Cart\Domain\CartStatus;
use App\Cart\Domain\Exception\CartNotFound;
use App\Shared\Money;

/**
 * Koszyki zapisywane jako pliki JSON: <katalog>/<cartId>.json. Rozwiązanie na potrzeby PoC;
 * w prawdziwej aplikacji w tym miejscu byłaby baza lub Redis.
 */
final class FileCartRepository implements CartRepository
{
    public function __construct(private readonly string $directory)
    {
    }

    public function get(string $id): Cart
    {
        $file = $this->path($id);
        if (!is_file($file)) {
            throw CartNotFound::withId($id);
        }

        $data = json_decode((string) file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);
        $items = array_map(static fn (array $row) => new CartItem(
            $row['productId'],
            $row['name'],
            new Money($row['unitPrice']),
            $row['quantity'],
        ), $data['items']);

        return Cart::restore($id, $items, $data['promoCode'], CartStatus::from($data['status']));
    }

    public function getOrCreate(string $id): Cart
    {
        return is_file($this->path($id)) ? $this->get($id) : new Cart($id);
    }

    public function save(Cart $cart): void
    {
        if (!is_dir($this->directory)) {
            mkdir($this->directory, 0775, true);
        }

        $data = [
            'status' => $cart->status()->value,
            'promoCode' => $cart->promoCode(),
            'items' => array_map(static fn (CartItem $i) => [
                'productId' => $i->productId,
                'name' => $i->name,
                'unitPrice' => $i->unitPrice->amount,
                'quantity' => $i->quantity,
            ], $cart->items()),
        ];

        file_put_contents($this->path($cart->id), json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }

    private function path(string $id): string
    {
        // Tylko znaki alfanumeryczne, żeby nie dało się wyjść poza katalog (path traversal).
        return $this->directory . '/' . preg_replace('/[^A-Za-z0-9_-]/', '', $id) . '.json';
    }
}
