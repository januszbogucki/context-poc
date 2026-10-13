<?php

declare(strict_types=1);

namespace App\Cart\Event;

use App\Cart\Domain\Cart;
use App\Order\Order;

final readonly class CartCheckedOut
{
    public function __construct(
        public Cart $cart,
        public Order $order,
    ) {
    }
}
