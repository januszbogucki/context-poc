<?php

declare(strict_types=1);

namespace App\Cart\Event;

use App\Catalog\ProductRepository;

/** Po złożeniu zamówienia zmniejsza stan magazynowy każdego zamówionego produktu. */
final class ReserveStockListener
{
    public function __construct(private readonly ProductRepository $products)
    {
    }

    public function __invoke(CartCheckedOut $event): void
    {
        foreach ($event->cart->items() as $item) {
            $product = $this->products->get($item->productId);
            $this->products->save($product->withStock(max(0, $product->stock - $item->quantity)));
        }
    }
}
