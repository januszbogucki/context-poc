<?php

declare(strict_types=1);

namespace App\Catalog\Http;

use App\Catalog\Product;
use App\Catalog\ProductRepository;
use App\Http\Request;
use App\Http\Response;

final class ProductController
{
    public function __construct(private readonly ProductRepository $products)
    {
    }

    public function list(Request $request): Response
    {
        return Response::json([
            'products' => array_map(static fn (Product $p) => $p->toArray(), $this->products->all()),
        ]);
    }

    public function show(Request $request): Response
    {
        return Response::json($this->products->get($request->attribute('id'))->toArray());
    }
}
