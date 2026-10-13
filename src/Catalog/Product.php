<?php

declare(strict_types=1);

namespace App\Catalog;

use App\Shared\Money;

final readonly class Product
{
    public function __construct(
        public string $id,
        public string $name,
        public Money $price,
        public int $stock,
    ) {
    }

    public function withStock(int $stock): self
    {
        return new self($this->id, $this->name, $this->price, $stock);
    }

    /** @return array<string, mixed> */
    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'price' => $this->price->toArray(),
            'stock' => $this->stock,
        ];
    }
}
