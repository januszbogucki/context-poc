<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

interface PromoCodeRepository
{
    public function find(string $code): ?PromoCode;
}
