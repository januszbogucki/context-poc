<?php

declare(strict_types=1);

namespace App\Cart\Domain;

use App\Cart\Domain\Exception\CartNotFound;

interface CartRepository
{
    /** @throws CartNotFound */
    public function get(string $id): Cart;

    /** Zwraca istniejący koszyk albo nowy (jeszcze niezapisany). */
    public function getOrCreate(string $id): Cart;

    public function save(Cart $cart): void;
}
