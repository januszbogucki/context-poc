<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

final readonly class PromoCode
{
    public function __construct(
        public string $code,
        public int $percent,
    ) {
    }
}
