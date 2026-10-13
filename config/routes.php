<?php

declare(strict_types=1);

use App\Cart\Http\CartController;
use App\Catalog\Http\ProductController;
use App\Http\Router;

return static function (Router $router): void {
    // Katalog
    $router->get('/products', [ProductController::class, 'list']);
    $router->get('/products/{id}', [ProductController::class, 'show']);

    // Koszyk (identyfikowany nagłówkiem X-Cart-Id)
    $router->get('/cart', [CartController::class, 'show']);
    $router->post('/cart/items', [CartController::class, 'addItem']);
    $router->patch('/cart/items/{productId}', [CartController::class, 'changeQuantity']);
    $router->delete('/cart/items/{productId}', [CartController::class, 'removeItem']);
    $router->post('/cart/promo', [CartController::class, 'applyPromo']);
    $router->post('/cart/checkout', [CartController::class, 'checkout']);
};
