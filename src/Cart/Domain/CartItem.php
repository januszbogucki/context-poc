<?php

declare(strict_types=1);

namespace App\Cart\Domain;

use App\Shared\Money;

/**
 * Pozycja koszyka. Przechowuje nazwę i cenę z chwili dodania (snapshot), więc późniejsza zmiana
 * ceny w katalogu nie zmienia zawartości istniejących koszyków.
 */
final readonly class CartItem
{
    public function __construct(
        public string $productId,
        public string $name,
        public Money $unitPrice,
        public int $quantity,
    ) {
    }

    public function withQuantity(int $quantity): self
    {
        return new self($this->productId, $this->name, $this->unitPrice, $quantity);
    }

    public function lineTotal(): Money
    {
        return $this->unitPrice->multiply($this->quantity);
    }

    /** @return array<string, mixed> */
    public function toArray(): array
    {
        return [
            'productId' => $this->productId,
            'name' => $this->name,
            'unitPrice' => $this->unitPrice->toArray(),
            'quantity' => $this->quantity,
            'lineTotal' => $this->lineTotal()->toArray(),
        ];
    }
}
