<?php

declare(strict_types=1);

namespace App\Catalog;

use App\Shared\Exception\NotFoundException;

final class ProductNotFound extends NotFoundException
{
    public static function withId(string $id): self
    {
        return new self("Product not found: {$id}");
    }
}
