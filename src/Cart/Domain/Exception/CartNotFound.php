<?php

declare(strict_types=1);

namespace App\Cart\Domain\Exception;

use App\Shared\Exception\NotFoundException;

final class CartNotFound extends NotFoundException
{
    public static function withId(string $id): self
    {
        return new self("Cart not found: {$id}");
    }
}
