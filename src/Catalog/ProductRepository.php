<?php

declare(strict_types=1);

namespace App\Catalog;

interface ProductRepository
{
    /** @return list<Product> */
    public function all(): array;

    /** @throws ProductNotFound */
    public function get(string $id): Product;

    public function save(Product $product): void;
}
