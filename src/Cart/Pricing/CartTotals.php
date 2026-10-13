<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Shared\Money;

final readonly class CartTotals
{
    public function __construct(
        public Money $subtotal,
        public Money $discount,
        public Money $shipping,
        public Money $total,
    ) {
    }

    /** @return array<string, array<string, mixed>> */
    public function toArray(): array
    {
        return [
            'subtotal' => $this->subtotal->toArray(),
            'discount' => $this->discount->toArray(),
            'shipping' => $this->shipping->toArray(),
            'total' => $this->total->toArray(),
        ];
    }
}
