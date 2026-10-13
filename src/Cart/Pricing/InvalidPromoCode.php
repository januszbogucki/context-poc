<?php

declare(strict_types=1);

namespace App\Cart\Pricing;

use App\Shared\Exception\DomainException;

final class InvalidPromoCode extends DomainException
{
    public static function withCode(string $code): self
    {
        return new self("Invalid promo code: {$code}");
    }
}
