# Mapa repozytorium (wygenerowana automatycznie)

Plik generuje `scripts/update-context.sh` (lokalnie lub w GitHub Action `update-context`).
**Nie edytuj ręcznie**, zmiany zostaną nadpisane przy następnym uruchomieniu.

Zawiera klasy i sygnatury metod z numerami linii. Nie opisuje powiązań między klasami ani reguł biznesowych.

```
src/Auth/ApiTokenProvider.php:
  11: final class ApiTokenProvider
  13:     public function token(): string

src/Cart/Application/CartService.php:
  19: final class CartService
  21:     public function __construct(
  29:     public function show(string $cartId): Cart
  34:     public function totals(Cart $cart): CartTotals
  39:     public function addItem(string $cartId, string $productId, int $quantity): Cart
  48:     public function changeQuantity(string $cartId, string $productId, int $quantity): Cart
  57:     public function removeItem(string $cartId, string $productId): Cart
  66:     public function applyPromoCode(string $cartId, string $code): Cart

src/Cart/Application/CheckoutService.php:
  19: final class CheckoutService
  21:     public function __construct(
  29:     public function checkout(string $cartId): Order

src/Cart/Domain/Cart.php:
  17: final class Cart
  26:     public function __construct(public readonly string $id)
  30:     public function addProduct(Product $product, int $quantity): void
  41:     public function changeQuantity(Product $product, int $quantity): void
  51:     public function removeProduct(string $productId): void
  57:     public function applyPromoCode(string $code): void
  63:     public function markCheckedOut(): void
  70:     public function items(): array
  75:     public function isEmpty(): bool
  80:     public function promoCode(): ?string
  85:     public function status(): CartStatus
  90:     public function subtotal(): Money
 104:     public static function restore(string $id, array $items, ?string $promoCode, CartStatus $status): self
 116:     private function assertOpen(): void
 123:     private function assertQuantity(int $quantity): void
 130:     private function assertInStock(Product $product, int $quantity): void

src/Cart/Domain/CartItem.php:
  13: final readonly class CartItem
  15:     public function __construct(
  23:     public function withQuantity(int $quantity): self
  28:     public function lineTotal(): Money
  34:     public function toArray(): array

src/Cart/Domain/CartRepository.php:
  12:     public function get(string $id): Cart;
  15:     public function getOrCreate(string $id): Cart;
  17:     public function save(Cart $cart): void;

src/Cart/Domain/Exception/CartAlreadyCheckedOut.php:
   9: final class CartAlreadyCheckedOut extends DomainException

src/Cart/Domain/Exception/CartNotFound.php:
   9: final class CartNotFound extends NotFoundException
  11:     public static function withId(string $id): self

src/Cart/Domain/Exception/EmptyCart.php:
   9: final class EmptyCart extends DomainException

src/Cart/Domain/Exception/InsufficientStock.php:
   9: final class InsufficientStock extends DomainException

src/Cart/Domain/Exception/InvalidQuantity.php:
   9: final class InvalidQuantity extends DomainException

src/Cart/Event/CartCheckedOut.php:
  10: final readonly class CartCheckedOut
  12:     public function __construct(

src/Cart/Event/LogCheckoutListener.php:
   8: final class LogCheckoutListener
  10:     public function __construct(private readonly string $logFile)
  14:     public function __invoke(CartCheckedOut $event): void

src/Cart/Event/ReserveStockListener.php:
  10: final class ReserveStockListener
  12:     public function __construct(private readonly ProductRepository $products)
  16:     public function __invoke(CartCheckedOut $event): void

src/Cart/Http/CartController.php:
  18: final class CartController
  20:     public function __construct(
  26:     public function show(Request $request): Response
  33:     public function addItem(Request $request): Response
  45:     public function changeQuantity(Request $request): Response
  57:     public function removeItem(Request $request): Response
  64:     public function applyPromo(Request $request): Response
  72:     public function checkout(Request $request): Response
  79:     private function cartId(Request $request): string
  84:     private function cartResponse(Cart $cart, int $status, string $cartId): Response

src/Cart/Infrastructure/FileCartRepository.php:
  18: final class FileCartRepository implements CartRepository
  20:     public function __construct(private readonly string $directory)
  24:     public function get(string $id): Cart
  42:     public function getOrCreate(string $id): Cart
  47:     public function save(Cart $cart): void
  67:     private function path(string $id): string

src/Cart/Pricing/BulkDiscount.php:
  11: final class BulkDiscount implements DiscountPolicy
  16:     public function discountFor(Cart $cart, Money $subtotal): Money

src/Cart/Pricing/CartTotals.php:
   9: final readonly class CartTotals
  11:     public function __construct(
  20:     public function toArray(): array

src/Cart/Pricing/DiscountPolicy.php:
  13:     public function discountFor(Cart $cart, Money $subtotal): Money;

src/Cart/Pricing/InMemoryPromoCodeRepository.php:
   8: final class InMemoryPromoCodeRepository implements PromoCodeRepository
  13:     public function __construct()
  21:     public function find(string $code): ?PromoCode

src/Cart/Pricing/InvalidPromoCode.php:
   9: final class InvalidPromoCode extends DomainException
  11:     public static function withCode(string $code): self

src/Cart/Pricing/PricingCalculator.php:
  15: final class PricingCalculator
  18:     public function __construct(
  24:     public function calculate(Cart $cart): CartTotals

src/Cart/Pricing/PromoCode.php:
   7: final readonly class PromoCode
   9:     public function __construct(

src/Cart/Pricing/PromoCodeDiscount.php:
  11: final class PromoCodeDiscount implements DiscountPolicy
  13:     public function __construct(private readonly PromoCodeRepository $promoCodes)
  17:     public function discountFor(Cart $cart, Money $subtotal): Money

src/Cart/Pricing/PromoCodeRepository.php:
   9:     public function find(string $code): ?PromoCode;

src/Cart/Pricing/ShippingCalculator.php:
  10: final class ShippingCalculator
  15:     public function costFor(Money $amountAfterDiscounts): Money

src/Catalog/Http/ProductController.php:
  12: final class ProductController
  14:     public function __construct(private readonly ProductRepository $products)
  18:     public function list(Request $request): Response
  25:     public function show(Request $request): Response

src/Catalog/JsonProductRepository.php:
  14: final class JsonProductRepository implements ProductRepository
  16:     public function __construct(
  22:     public function all(): array
  27:     public function get(string $id): Product
  32:     public function save(Product $product): void
  48:     private function load(): array

src/Catalog/Product.php:
   9: final readonly class Product
  11:     public function __construct(
  19:     public function withStock(int $stock): self
  25:     public function toArray(): array

src/Catalog/ProductNotFound.php:
   9: final class ProductNotFound extends NotFoundException
  11:     public static function withId(string $id): self

src/Catalog/ProductRepository.php:
  10:     public function all(): array;
  13:     public function get(string $id): Product;
  15:     public function save(Product $product): void;

src/Container/Container.php:
  13: final class Container
  22:     public function set(string $id, Closure $factory): void
  33:     public function get(string $id): object

src/Http/Request.php:
   7: final class Request
  14:     public function __construct(
  23:     public static function fromGlobals(): self
  43:     public function header(string $name): ?string
  48:     public function attribute(string $name): string
  54:     public function withAttributes(array $attributes): self

src/Http/Response.php:
   7: final class Response
  12:     public function __construct(
  20:     public static function json(array $data, int $status = 200, array $headers = []): self
  29:     public function send(): void

src/Http/Router.php:
  14: final class Router
  20:     public function get(string $pattern, array $handler): void
  26:     public function post(string $pattern, array $handler): void
  32:     public function patch(string $pattern, array $handler): void
  38:     public function delete(string $pattern, array $handler): void
  44:     private function add(string $method, string $pattern, array $handler): void
  50:     public function dispatch(Request $request, Container $container): Response

src/Kernel.php:
  18: final class Kernel
  22:     public function __construct(private readonly string $projectDir)
  29:     public function container(): Container
  34:     public function handle(Request $request): Response

src/Order/Order.php:
  11: final readonly class Order
  14:     public function __construct(
  24:     public function toArray(): array

src/Order/OrderFactory.php:
  12: final class OrderFactory
  14:     public function fromCart(Cart $cart, CartTotals $totals): Order

src/Payment/PaymentGateway.php:
  12:     public function charge(int $amountInGrosze, string $currency): bool;

src/Shared/EventDispatcher.php:
  11: final class EventDispatcher
  17:     public function listen(string $eventClass, callable $listener): void
  22:     public function dispatch(object $event): void

src/Shared/Exception/DomainException.php:
  10: class DomainException extends RuntimeException

src/Shared/Exception/NotFoundException.php:
   8: class NotFoundException extends DomainException

src/Shared/Money.php:
  12: final readonly class Money
  14:     public function __construct(
  20:     public static function zero(string $currency = 'PLN'): self
  25:     public function add(self $other): self
  31:     public function subtract(self $other): self
  37:     public function multiply(int $factor): self
  43:     public function percent(int $percent): self
  48:     public function isZero(): bool
  53:     public function isGreaterThanOrEqual(self $other): bool
  59:     public function min(self $other): self
  65:     public function toArray(): array
  74:     private function assertSameCurrency(self $other): void
```
