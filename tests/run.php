<?php

declare(strict_types=1);

/**
 * Minimalny runner testów bez zależności: php tests/run.php
 * Każdy test to funkcja zarejestrowana przez test(); assertSame() rzuca wyjątek przy różnicy.
 */

use App\Cart\Domain\Cart;
use App\Cart\Domain\Exception\InsufficientStock;
use App\Cart\Pricing\BulkDiscount;
use App\Cart\Pricing\InMemoryPromoCodeRepository;
use App\Cart\Pricing\PricingCalculator;
use App\Cart\Pricing\PromoCodeDiscount;
use App\Cart\Pricing\ShippingCalculator;
use App\Catalog\Product;
use App\Shared\Money;

require __DIR__ . '/../vendor/autoload.php';

$failed = 0;

function test(string $name, callable $fn): void
{
    global $failed;
    try {
        $fn();
        echo "ok   {$name}\n";
    } catch (Throwable $e) {
        $failed++;
        echo "FAIL {$name}: {$e->getMessage()}\n";
    }
}

function assertSame(mixed $expected, mixed $actual): void
{
    if ($expected !== $actual) {
        throw new RuntimeException('expected ' . var_export($expected, true) . ', got ' . var_export($actual, true));
    }
}

function calculator(): PricingCalculator
{
    return new PricingCalculator(
        [new PromoCodeDiscount(new InMemoryPromoCodeRepository()), new BulkDiscount()],
        new ShippingCalculator(),
    );
}

$mug = new Product('p-100', 'Kubek', new Money(2999), 50);
$backpack = new Product('p-103', 'Plecak', new Money(17900), 15);

test('adding the same product twice sums quantity', function () use ($mug) {
    $cart = new Cart('c1');
    $cart->addProduct($mug, 1);
    $cart->addProduct($mug, 2);
    assertSame(3, $cart->items()[0]->quantity);
});

test('cannot add more than in stock', function () {
    $cart = new Cart('c1');
    $product = new Product('p-104', 'Lampka', new Money(8900), 2);
    try {
        $cart->addProduct($product, 3);
        throw new RuntimeException('expected InsufficientStock');
    } catch (InsufficientStock) {
    }
});

test('shipping is 15 PLN below 200 PLN', function () use ($mug) {
    $cart = new Cart('c1');
    $cart->addProduct($mug, 1); // 29,99
    $totals = calculator()->calculate($cart);
    assertSame(1500, $totals->shipping->amount);
    assertSame(4499, $totals->total->amount);
});

test('shipping is free from 200 PLN', function () use ($backpack) {
    $cart = new Cart('c1');
    $cart->addProduct($backpack, 2); // 358,00
    assertSame(0, calculator()->calculate($cart)->shipping->amount);
});

test('promo code and bulk discount add up', function () use ($backpack) {
    $cart = new Cart('c1');
    $cart->addProduct($backpack, 3); // 537,00 -> 10% + 5%
    $cart->applyPromoCode('WELCOME10');
    $totals = calculator()->calculate($cart);
    assertSame(53700, $totals->subtotal->amount);
    assertSame(5370 + 2685, $totals->discount->amount);
    assertSame(53700 - 8055, $totals->total->amount);
});

echo $failed === 0 ? "\nAll tests passed\n" : "\n{$failed} test(s) failed\n";
exit($failed === 0 ? 0 : 1);
