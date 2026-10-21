# Kontekst aplikacji

Kontekst zbudowano na podstawie kodu aplikacji z katalogu `src/`, uzupełnionego o konfigurację z `config/`, punkt wejścia i pliki PHP z `public/`, `composer.json`, `data/products.json` oraz mapę repozytorium.
Pliki objęte wykluczeniami generatora są pomijane.
Wygenerowano automatycznie przez Claude. Zweryfikuj szczegóły w kodzie przed zmianą.

## Architektura

Aplikacja to mini sklep w PHP bez frameworka (`composer.json`: `demo/mini-shop`). Udostępnia JSON API z katalogiem produktów, koszykiem i składaniem zamówienia. Autoload PSR-4 mapuje `App\` na `src/`.

**Punkt wejścia i jądro**
- `public/index.php` ładuje `vendor/autoload.php` i tworzy `App\Kernel` z katalogiem projektu. Następnie wywołuje `Kernel::handle(Request::fromGlobals())->send()`.
- `src/Kernel.php` (`Kernel`):
  - Konstruktor tworzy `Container` i wywołuje funkcję zwracaną przez `config/services.php`.
  - `handle()` przy każdym żądaniu tworzy nowy `Router`, ładuje `config/routes.php` i wywołuje `Router::dispatch()`.
  - Wyjątki są mapowane na odpowiedzi HTTP (szczegóły w „Dane i API”).
  - `container()` udostępnia kontener na zewnątrz.

**Warstwa HTTP (`src/Http/`)**
- `Request` (`Request::fromGlobals`):
  - Zbiera nagłówki z `$_SERVER['HTTP_*']`. Klucze zapisuje małymi literami, a `_` zamienia na `-`.
  - Body dekoduje jako JSON. Niepoprawny JSON lub wartość niebędąca tablicą daje `[]`.
  - Metodę zapisuje wielkimi literami, a ścieżkę wyznacza przez `parse_url`.
  - `header()` jest niewrażliwe na wielkość liter. `attribute()` zwraca `''`, gdy parametru brak.
- `Response`: `Response::json()` ustawia `Content-Type: application/json` i koduje dane z `JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES`. `send()` wysyła status, nagłówki i treść.
- `Router`:
  - Wzorce `{nazwa}` są zamieniane na regex `(?P<nazwa>[^/]+)` z kotwicami `^…$`.
  - Wygrywa pierwsza trasa o zgodnej metodzie i ścieżce.
  - Kontroler jest pobierany z kontenera (`Container::get`), a parametry trasy trafiają do `Request::withAttributes`.
  - Brak dopasowania rzuca `NotFoundException("Route not found: …")`. Dotyczy to także złej metody, więc nie ma odpowiedzi 405.
  - Parametry nie są dekodowane z URL. Ukośnik na końcu ścieżki powoduje brak dopasowania.

**Kontener DI**
- `src/Container/Container.php` (`Container`) przechowuje fabryki `Closure(Container)` rejestrowane ręcznie, bez autowiringu.
- Instancje są współdzielone, czyli tworzone leniwie raz na proces/żądanie. `set()` usuwa wcześniej utworzoną instancję.
- Niezarejestrowana usługa rzuca `RuntimeException`, co daje HTTP 500.

**Rejestracje w `config/services.php`**
- `ProductRepository` → `JsonProductRepository(data/products.json, var/products.json)`.
- `CartRepository` → `FileCartRepository(var/carts)`.
- `PromoCodeRepository` → `InMemoryPromoCodeRepository`.
- `PricingCalculator` → polityki `[PromoCodeDiscount, BulkDiscount]` oraz `ShippingCalculator`.
- `CartService(CartRepository, ProductRepository, PromoCodeRepository, PricingCalculator)`.
- `CheckoutService(CartRepository, PricingCalculator, new OrderFactory(), EventDispatcher)`.
- Kontrolery: `ProductController`, `CartController`.
- `EventDispatcher` z listenerami `CartCheckedOut`, wywoływanymi w kolejności: `ReserveStockListener`, potem `LogCheckoutListener(var/checkout.log)`.

**Moduły**
- `src/Catalog/`: encja `Product` (readonly; `withStock`, `toArray`), interfejs `ProductRepository`, implementacja `JsonProductRepository`, wyjątek `ProductNotFound`, kontroler `Http/ProductController`.
- `src/Cart/Domain/`: agregat `Cart`, `CartItem`, enum `CartStatus` (`open`, `checked_out`), interfejs `CartRepository` oraz wyjątki domenowe.
- `src/Cart/Application/`: przypadki użycia w `CartService` i `CheckoutService`.
- `src/Cart/Pricing/`: wycena, czyli `PricingCalculator`, `DiscountPolicy`, `PromoCodeDiscount`, `BulkDiscount`, `ShippingCalculator`, `CartTotals` i kody rabatowe.
- `src/Cart/Infrastructure/FileCartRepository.php`: zapis koszyków do plików JSON.
- `src/Cart/Event/`: zdarzenie `CartCheckedOut(Cart, Order)` i jego listenery.
- `src/Cart/Http/CartController.php`: endpointy koszyka.
- `src/Order/`: `Order` (readonly) i `OrderFactory`.
- `src/Shared/`: `Money`, synchroniczny `EventDispatcher`, wyjątki bazowe `DomainException` (rozszerza `RuntimeException`) i `NotFoundException` (rozszerza `DomainException`).
- `src/Auth/ApiTokenProvider.php` i `src/Payment/PaymentGateway.php` są oznaczone w komentarzach jako fixture do testu wykluczeń mapy. Nie są zarejestrowane w kontenerze ani używane przez inny kod.

## Przepływy

**Żądanie HTTP**
1. `public/index.php` wywołuje `Request::fromGlobals()`, a potem `Kernel::handle()`.
2. `Kernel::handle()` uruchamia `Router::dispatch()`, który wywołuje metodę kontrolera z kontenera.
3. Kontroler zwraca `Response`, a ostatni krok to `Response::send()`.
4. Wyjątki są przechwytywane w `Kernel::handle()`.

**Identyfikacja koszyka** (`CartController::cartId`)
- Koszyk wskazuje nagłówek `X-Cart-Id`. Gdy go brak, generowany jest nowy identyfikator: `bin2hex(random_bytes(8))`, czyli 16 znaków hex.
- Każda odpowiedź koszyka zwraca identyfikator w nagłówku `X-Cart-Id`.
- Nowy identyfikator wskazuje koszyk nieistniejący w repozytorium. Działa więc tylko z operacjami opartymi o `getOrCreate`.

**Koszyk** (`CartService`)
- `show`: `CartRepository::getOrCreate`, bez zapisu. Nowy koszyk nie jest utrwalany przez `GET /cart`.
- `addItem`:
  - Wywołuje `getOrCreate`, potem `ProductRepository::get` (404, gdy brak produktu), `Cart::addProduct` i `save`.
  - Jako jedyna operacja tworzy plik koszyka.
- `changeQuantity`: `get` (404 `CartNotFound`, gdy brak pliku), potem `ProductRepository::get`, `Cart::changeQuantity` i `save`.
- `removeItem`: `get`, potem `Cart::removeProduct` i `save`. Nie sprawdza istnienia produktu w katalogu.
- `applyPromoCode`:
  - Najpierw waliduje kod przez `PromoCodeRepository::find`. Błędny kod daje `InvalidPromoCode`, jeszcze przed wczytaniem koszyka.
  - Następnie wywołuje `get`, `Cart::applyPromoCode(strtoupper($code))` i `save`.
- Po każdej operacji `CartController::cartResponse` liczy sumy przez `CartService::totals`, czyli `PricingCalculator::calculate`.

**Wycena** (`PricingCalculator::calculate`)
1. `subtotal = Cart::subtotal()`, czyli suma `CartItem::lineTotal()`.
2. Rabat to suma `discountFor()` wszystkich polityk, z których każda liczy od tego samego `subtotal`. Wynik jest ograniczony przez `Money::min($subtotal)`.
3. `afterDiscount = subtotal − discount`.
4. `shipping = ShippingCalculator::costFor(afterDiscount)`.
5. `total = afterDiscount + shipping`. Wynik to `CartTotals(subtotal, discount, shipping, total)`.

**Checkout → zamówienie → zdarzenia** (`CheckoutService::checkout`)
1. `CartRepository::get`. Brak koszyka daje 404.
2. Pusty koszyk powoduje `EmptyCart('Cannot check out an empty cart')`, co daje 422.
3. Sumy są liczone przez `PricingCalculator::calculate`.
4. `Cart::markCheckedOut()` rzuca `CartAlreadyCheckedOut` (422), jeśli koszyk był już zamknięty. Potem następuje `save`.
5. `OrderFactory::fromCart` tworzy `Order` z id `ORD-` + 8 wielkich znaków hex, pozycjami koszyka, sumami i `createdAt`.
6. `EventDispatcher::dispatch(new CartCheckedOut($cart, $order))` działa synchronicznie, w kolejności rejestracji:
   - `ReserveStockListener`: dla każdej pozycji wywołuje `ProductRepository::get` i `save(withStock(max(0, stock − quantity)))`.
   - `LogCheckoutListener`: dopisuje linię `"<date('c')> order=<id> cart=<cartId> total=<grosze>"` do `var/checkout.log`.
7. Kontroler zwraca `Order::toArray()` ze statusem 201.

Zamówienie nie jest nigdzie zapisywane poza odpowiedzią i linią logu. Nie istnieje repozytorium zamówień. Nie ma też płatności, bo `PaymentGateway` nie jest wywoływany.

Koszyk jest zapisany jako zamknięty przed uruchomieniem listenerów. Jeśli listener rzuci wyjątek, na przykład `ProductNotFound` dla produktu usuniętego z katalogu, klient dostanie błąd, a koszyk pozostanie zamknięty. Kod nie zawiera mechanizmu wycofania.

## Reguły biznesowe

**Ilość i stan koszyka** (`src/Cart/Domain/Cart.php`, `Cart`)
- `assertOpen`: każda mutacja, czyli `addProduct`, `changeQuantity`, `removeProduct`, `applyPromoCode` i `markCheckedOut`, wymaga statusu `CartStatus::Open`. W przeciwnym razie rzuca `CartAlreadyCheckedOut` (422).
- `assertQuantity`: ilość musi wynosić co najmniej 1, inaczej rzuca `InvalidQuantity`.
- `addProduct`:
  - Nowa ilość to suma dotychczasowej i dodawanej. Jest sprawdzana względem `Product::stock`.
  - Pozycja jest tworzona na nowo z aktualną nazwą i ceną produktu. Ponowne dodanie produktu aktualizuje więc cenę jednostkową całej pozycji.
- `changeQuantity`:
  - Kolejność sprawdzeń: open, ilość, stan magazynu, istnienie pozycji (`InvalidQuantity "Product … is not in the cart"`).
  - Zachowuje dotychczasową cenę przez `CartItem::withQuantity`.
- `removeProduct` nie zgłasza błędu, gdy pozycji brak.
- Koszyk przechowuje jeden kod rabatowy. Kolejne `applyPromoCode` nadpisuje poprzedni. Nie ma operacji usunięcia kodu.
- `Cart::restore` odtwarza stan z zapisu z pominięciem walidacji.

**Zapasy**
- Stan magazynu jest sprawdzany tylko przy dodawaniu i zmianie ilości (`Cart::assertInStock`). Zakres sprawdzenia obejmuje tylko ten koszyk.
- `CheckoutService` nie sprawdza zapasów ponownie.
- `ReserveStockListener` zmniejsza stan, obcinając go do 0 przez `max(0, …)`. Sprzedaż ponad stan nie zgłasza więc błędu.
- Nie ma blokowania ani rezerwacji między koszykami.

**Snapshot ceny**: `CartItem` przechowuje nazwę i `unitPrice` z chwili dodania (`src/Cart/Domain/CartItem.php`). Zastrzeżenie dotyczące ponownego `addProduct` opisano wyżej.

**Kody rabatowe** (`InMemoryPromoCodeRepository`)
- Dostępne kody: `WELCOME10` (10%) i `SUMMER20` (20%).
- `find()` porównuje kody bez względu na wielkość liter, przez `strtoupper`.
- `PromoCodeDiscount::discountFor` zwraca procent `subtotal` dla kodu zapisanego w koszyku. Jeśli kodu nie ma już w repozytorium, rabat wynosi zero.

**Rabat ilościowy** (`BulkDiscount`): 5% (`PERCENT`) przy `subtotal ≥ 50_000` groszy, czyli 500,00 PLN (`THRESHOLD_GROSZE`). Próg dotyczy kwoty przed rabatami.

**Łączenie rabatów** (`PricingCalculator::calculate`)
- Rabaty sumują się. Każdy jest liczony od pierwotnego `subtotal`, a nie kaskadowo.
- Kolejność polityk z `config/services.php` (najpierw promo, potem bulk) nie wpływa na wynik.
- Suma rabatów nie przekroczy `subtotal`.

**Dostawa** (`ShippingCalculator::costFor`)
- Kwota po rabatach równa 0 daje dostawę 0.
- Kwota `≥ 20_000` groszy (200,00 PLN, `FREE_FROM_GROSZE`) daje dostawę 0.
- W pozostałych przypadkach dostawa kosztuje `1_500` groszy (15,00 PLN, `FLAT_RATE_GROSZE`).
- Próg liczony jest po rabatach, więc kod rabatowy może spowodować naliczenie dostawy.

**Pieniądze i zaokrąglenia** (`src/Shared/Money.php`, `Money`)
- Kwoty są przechowywane jako `int` w groszach. Domyślna waluta to `PLN`.
- `percent()` zaokrągla w dół przez `intdiv`. Każda polityka rabatowa zaokrągla osobno.
- `add`, `subtract` i `isGreaterThanOrEqual` przy różnych walutach rzucają `InvalidArgumentException` (HTTP 500). `min` i `multiply` nie sprawdzają waluty.
- `toArray()` zwraca `{amount, currency, formatted}`, gdzie `formatted` ma postać `"%d,%02d %s"`, np. `29,99 PLN`.
- Waluta nie jest zapisywana w plikach. `FileCartRepository` i `JsonProductRepository` odtwarzają kwoty jako PLN.
- `ShippingCalculator` tworzy kwoty zawsze w PLN.

**Dane startowe** (`data/products.json`)
- 5 produktów, od `p-100` do `p-104`.
- Ceny w groszach, np. `p-100` kosztuje 2999. `p-104` (Lampka biurkowa) ma stan 2.

## Dane i API

Trasy zdefiniowano w `config/routes.php`. Wszystkie odpowiedzi to JSON.

| Metoda | Ścieżka | Handler | Wejście | Sukces |
|---|---|---|---|---|
| GET | `/products` | `ProductController::list` | — | 200 `{products: [Product]}` |
| GET | `/products/{id}` | `ProductController::show` | `id` w ścieżce | 200 `Product` |
| GET | `/cart` | `CartController::show` | `X-Cart-Id` | 200 koszyk |
| POST | `/cart/items` | `CartController::addItem` | body `productId` (string, domyślnie `''`), `quantity` (int, domyślnie 1) | 201 koszyk |
| PATCH | `/cart/items/{productId}` | `CartController::changeQuantity` | body `quantity` (int, domyślnie 0, co daje 422) | 200 koszyk |
| DELETE | `/cart/items/{productId}` | `CartController::removeItem` | — | 200 koszyk |
| POST | `/cart/promo` | `CartController::applyPromo` | body `code` (domyślnie `''`) | 200 koszyk |
| POST | `/cart/checkout` | `CartController::checkout` | — | 201 zamówienie |

Wartości z body są rzutowane przez `(int)` lub `(string)`. Na przykład nieliczbowa `quantity` daje 0, a w konsekwencji 422.

**Format danych**
- `Product::toArray`: `{id, name, price: Money, stock}`.
- Koszyk (`CartController::cartResponse`): `{id, status, promoCode, items: [CartItem], totals}`.
- `CartItem::toArray`: `{productId, name, unitPrice, quantity, lineTotal}`.
- `CartTotals::toArray`: `{subtotal, discount, shipping, total}`, każde pole w formacie `Money`.
- Zamówienie (`Order::toArray`): `{id, cartId, items, totals, createdAt (ISO 8601)}`.
- Odpowiedzi koszyka i checkoutu mają nagłówek `X-Cart-Id`.

**Błędy** (`Kernel::handle`): treść odpowiedzi to `{"error": "<komunikat>"}`.

| Status | Wyjątki |
|---|---|
| 404 | `NotFoundException`: `CartNotFound`, `ProductNotFound`, brak trasy |
| 422 | pozostałe `DomainException`: `InvalidQuantity`, `InsufficientStock`, `EmptyCart`, `CartAlreadyCheckedOut`, `InvalidPromoCode` |
| 500 | każdy inny `Throwable` (`Internal server error`), np. błąd JSON w plikach danych, niezgodność walut, brak usługi w kontenerze |

**Zapis danych**
- Koszyki (`FileCartRepository`):
  - Każdy koszyk to plik `var/carts/<id>.json` z polami `status`, `promoCode` oraz `items` (`productId`, `name`, `unitPrice` w groszach, `quantity`).
  - `save()` tworzy katalog z uprawnieniami `0775`.
  - `path()` usuwa z id znaki spoza `[A-Za-z0-9_-]`. Różne wartości `X-Cart-Id` mogą więc wskazywać ten sam plik, podczas gdy `Cart::id`, `Order::cartId` i log zawierają surową wartość nagłówka.
- Produkty (`JsonProductRepository`):
  - Odczyt pochodzi z `var/products.json`, jeśli plik istnieje, a w przeciwnym razie z `data/products.json`.
  - `save()` nadpisuje cały plik `var/products.json`, nie tworząc katalogu.
- Log zamówień: `var/checkout.log`, w trybie dopisywania.
- Zapisy plików nie używają blokad. Kod nie zapewnia atomowości operacji obejmujących kilka plików.

## Praca z projektem

**Wymagania i komendy** (`composer.json`)
- PHP `>=8.3`. Nie ma zależności zewnętrznych.
- `public/index.php` wymaga `vendor/autoload.php`, więc potrzebne jest wygenerowanie autoloadu Composera.
- `composer serve` uruchamia `php -S localhost:8080 -t public`.
- `composer test` uruchamia `php tests/run.php`. Implementacja testów nie została dołączona i testy nie były uruchamiane.
- Katalog `var/` jest zapisywalnym miejscem na dane runtime.

**Miejsca zmian dla typowych zadań**

| Zadanie | Gdzie zmieniać |
|---|---|
| Nowy rabat | nowa klasa implementująca `DiscountPolicy` (`src/Cart/Pricing/`) dopisana do listy w rejestracji `PricingCalculator` w `config/services.php` |
| Progi i stawki | `ShippingCalculator` (`FREE_FROM_GROSZE`, `FLAT_RATE_GROSZE`) oraz `BulkDiscount` (`THRESHOLD_GROSZE`, `PERCENT`). Zmiany wpływają na `CartTotals` w odpowiedziach koszyka, na checkout (`Order::totals`) i na wartość `total` w logu |
| Kody rabatowe | `InMemoryPromoCodeRepository` albo nowa implementacja `PromoCodeRepository` zarejestrowana w `config/services.php` |
| Nowy endpoint | trasa w `config/routes.php`, metoda kontrolera. Nowy kontroler trzeba zarejestrować w `config/services.php`, bo router pobiera kontrolery z kontenera |
| Reguły koszyka | `Cart` (`assert*`) i `CartService` |
| Checkout | `CheckoutService::checkout` |
| Reakcje po zamówieniu | nowy listener jako callable przyjmujący `CartCheckedOut`, zarejestrowany przez `EventDispatcher::listen` w `config/services.php`. Kolejność rejestracji wyznacza kolejność wykonania |
| Mapowanie błędów | `Kernel::handle` oraz hierarchia wyjątków w `src/Shared/Exception/` |
| Inny sposób przechowywania | implementacje `CartRepository` i `ProductRepository` podmienione w `config/services.php` |
| Format kwot | `Money::toArray` |

## Ograniczenia

- **Testy**: implementacja `tests/run.php` i katalogu testów nie została dostarczona. Nie wiadomo, co testy weryfikują ani czy przechodzą.
- **Mapa repozytorium**: opisuje strukturę, a nie zachowanie. Wspomina skrypt `scripts/update-context.sh` i GitHub Action `update-context`, których treści nie dostarczono. Enum `CartStatus` nie występuje w mapie, ale plik został udostępniony i opisany wyżej.
- **Wykluczenia generatora**: pliki pasujące do wzorców wykluczeń, np. sekrety, lokalne konfiguracje i testy, mogły zostać pominięte. Nie da się ustalić ich treści ani wpływu na działanie.
- **Fixture i interfejsy bez użycia**:
  - `src/Auth/ApiTokenProvider.php` zwraca zaszytą wartość tokenu. Jej nie przytoczono. Klasa nie jest zarejestrowana ani używana, a uwierzytelnianie API nie istnieje.
  - `src/Payment/PaymentGateway.php` to sam interfejs bez implementacji i wywołań. Checkout nie pobiera płatności.
- **Działający kod a deklaracje**: działającymi implementacjami są `JsonProductRepository`, `FileCartRepository` i `InMemoryPromoCodeRepository`. `CartRepository`, `ProductRepository`, `PromoCodeRepository`, `DiscountPolicy` i `PaymentGateway` to interfejsy.
- **Brakujące integracje**: nie ma bazy danych, trwałego zapisu zamówień, płatności, uwierzytelniania ani kolejki zdarzeń. Dispatcher działa synchronicznie, w tym samym żądaniu.
- **Zachowanie zapisu plików**:
  - Nie ustalono zachowania przy braku katalogu `var/` dla `var/products.json` i `var/checkout.log`. Te zapisy nie tworzą katalogu, a `file_put_contents` przy błędzie zwraca `false` bez wyjątku. Konfiguracja obsługi ostrzeżeń PHP nie została dostarczona.
  - W praktyce checkout wymaga istniejącego pliku koszyka, więc `var/` zwykle już istnieje po `FileCartRepository::save`.
- **Współbieżność**: brak blokad plików oznacza, że wynik równoległych żądań, np. dwóch checkoutów zmniejszających ten sam stan, nie jest określony przez kod.
- **Środowisko uruchomieniowe**: nie dostarczono konfiguracji serwera, CORS, wersji rozszerzeń PHP ani ustawień produkcyjnych.
