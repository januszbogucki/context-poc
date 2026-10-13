<?php

declare(strict_types=1);

use App\Cart\Application\CartService;
use App\Cart\Application\CheckoutService;
use App\Cart\Domain\CartRepository;
use App\Cart\Event\CartCheckedOut;
use App\Cart\Event\LogCheckoutListener;
use App\Cart\Event\ReserveStockListener;
use App\Cart\Http\CartController;
use App\Cart\Infrastructure\FileCartRepository;
use App\Cart\Pricing\BulkDiscount;
use App\Cart\Pricing\InMemoryPromoCodeRepository;
use App\Cart\Pricing\PricingCalculator;
use App\Cart\Pricing\PromoCodeDiscount;
use App\Cart\Pricing\PromoCodeRepository;
use App\Cart\Pricing\ShippingCalculator;
use App\Catalog\Http\ProductController;
use App\Catalog\JsonProductRepository;
use App\Catalog\ProductRepository;
use App\Container\Container;
use App\Order\OrderFactory;
use App\Shared\EventDispatcher;

/**
 * Rejestracja usług w kontenerze (ręczne DI, bez autowiringu).
 */
return static function (Container $c, string $projectDir): void {
    $c->set(EventDispatcher::class, static function (Container $c) {
        $dispatcher = new EventDispatcher();
        $dispatcher->listen(CartCheckedOut::class, $c->get(ReserveStockListener::class));
        $dispatcher->listen(CartCheckedOut::class, $c->get(LogCheckoutListener::class));
        return $dispatcher;
    });

    // Katalog
    $c->set(ProductRepository::class, static fn () => new JsonProductRepository(
        $projectDir . '/data/products.json',
        $projectDir . '/var/products.json',
    ));
    $c->set(ProductController::class, static fn (Container $c) => new ProductController(
        $c->get(ProductRepository::class),
    ));

    // Koszyk: repozytorium i ceny
    $c->set(CartRepository::class, static fn () => new FileCartRepository($projectDir . '/var/carts'));
    $c->set(PromoCodeRepository::class, static fn () => new InMemoryPromoCodeRepository());
    $c->set(PricingCalculator::class, static fn (Container $c) => new PricingCalculator(
        [
            new PromoCodeDiscount($c->get(PromoCodeRepository::class)),
            new BulkDiscount(),
        ],
        new ShippingCalculator(),
    ));

    // Koszyk: logika aplikacyjna
    $c->set(CartService::class, static fn (Container $c) => new CartService(
        $c->get(CartRepository::class),
        $c->get(ProductRepository::class),
        $c->get(PromoCodeRepository::class),
        $c->get(PricingCalculator::class),
    ));
    $c->set(CheckoutService::class, static fn (Container $c) => new CheckoutService(
        $c->get(CartRepository::class),
        $c->get(PricingCalculator::class),
        new OrderFactory(),
        $c->get(EventDispatcher::class),
    ));
    $c->set(CartController::class, static fn (Container $c) => new CartController(
        $c->get(CartService::class),
        $c->get(CheckoutService::class),
    ));

    // Listenery zdarzeń
    $c->set(ReserveStockListener::class, static fn (Container $c) => new ReserveStockListener(
        $c->get(ProductRepository::class),
    ));
    $c->set(LogCheckoutListener::class, static fn () => new LogCheckoutListener(
        $projectDir . '/var/checkout.log',
    ));
};
