<?php

declare(strict_types=1);

namespace App\Order;

use App\Cart\Domain\CartItem;
use App\Cart\Pricing\CartTotals;
use DateTimeImmutable;

final readonly class Order
{
    /** @param list<CartItem> $items */
    public function __construct(
        public string $id,
        public string $cartId,
        public array $items,
        public CartTotals $totals,
        public DateTimeImmutable $createdAt,
    ) {
    }

    /** @return array<string, mixed> */
    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'cartId' => $this->cartId,
            'items' => array_map(static fn (CartItem $i) => $i->toArray(), $this->items),
            'totals' => $this->totals->toArray(),
            'createdAt' => $this->createdAt->format('c'),
        ];
    }
}
