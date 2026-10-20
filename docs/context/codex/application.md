# Kontekst aplikacji

Kontekst zbudowano na podstawie kodu aplikacji z katalogu `src/`, uzupełnionego o konfigurację z `config/`, punkt wejścia i pliki PHP z `public/`, `composer.json`, `data/products.json` oraz mapę repozytorium.
Pliki objęte wykluczeniami generatora są pomijane.
Wygenerowano automatycznie przez Codex. Zweryfikuj szczegóły w kodzie przed zmianą.

## Architektura

Aplikacja jest mini sklepem HTTP bez frameworka. `composer.json` deklaruje PHP >=8.3 i autoloading PSR-4 `App\` → `src/`. Punkt wejścia `public/index.php` ładuje `vendor/autoload.php`, tworzy `Kernel`, buduje żądanie przez `Request::fromGlobals()` i wysyła odpowiedź przez `Response::send()`.

`src/Kernel.php`, `Kernel::__construct()`, tworzy kontener i wykonuje funkcję rejestrującą usługi z `config/services.php`. `Kernel::handle()` tworzy router, ładuje `config/routes.php`, uruchamia routing i mapuje wyjątki. `src/Container/Container.php`, `Container::set()` i `get()`, implementuje ręczne wstrzykiwanie zależności: fabryki są jawne, obiekty powstają przy pierwszym pobraniu i są współdzielone w danym kontenerze. Ponowna rejestracja usuwa zapamiętaną instancję; brak rejestracji powoduje `RuntimeException`.

Podział odpowiedzialności:

- Katalog: `src/Catalog/Product.php`, `Product`, opisuje produkt; `src/Catalog/JsonProductRepository.php`, `JsonProductRepository`, realizuje kontrakt `src/Catalog/ProductRepository.php`, `ProductRepository`. `src/Catalog/Http/ProductController.php`, `ProductController::list()` i `show()`, udostępnia odczyt produktów.
- Koszyk: `src/Cart/Domain/Cart.php`, `Cart`, pilnuje zmian agregatu; `src/Cart/Domain/CartItem.php`, `CartItem`, przechowuje pozycję. `src/Cart/Application/CartService.php`, `CartService`, koordynuje repozytoria i wycenę.
- Wycena: `src/Cart/Pricing/PricingCalculator.php`, `PricingCalculator::calculate()`, łączy polityki `DiscountPolicy::discountFor()` z `src/Cart/Pricing/DiscountPolicy.php` oraz kalkulatorem dostawy.
- Checkout: `src/Cart/Application/CheckoutService.php`, `CheckoutService::checkout()`, zamyka koszyk, tworzy zamówienie i publikuje zdarzenie. `src/Order/OrderFactory.php`, `OrderFactory::fromCart()`, buduje `Order`.
- Infrastruktura: `src/Cart/Infrastructure/FileCartRepository.php`, `FileCartRepository`, zapisuje koszyki; `src/Shared/EventDispatcher.php`, `EventDispatcher`, synchronicznie wywołuje listenery.

`config/services.php` wiąże `CartRepository` z `FileCartRepository`, `ProductRepository` z `JsonProductRepository`, a `PromoCodeRepository` z `InMemoryPromoCodeRepository`. Do wyceny przekazuje kolejno `PromoCodeDiscount` i `BulkDiscount`. Dla `CartCheckedOut` rejestruje najpierw `ReserveStockListener`, następnie `LogCheckoutListener`.

## Przepływy

`src/Http/Request.php`, `Request::fromGlobals()`, odczytuje metodę, ścieżkę bez query string, nagłówki serwera `HTTP_*` oraz JSON z ciała. Nazwy nagłówków zamienia na małe litery. Niepoprawny JSON, JSON `null` lub wartość niebędąca tablicą daje puste ciało. Kod nie sprawdza `Content-Type`.

`src/Http/Router.php`, `Router::add()` i `dispatch()`, dopasowuje metodę oraz całą ścieżkę wyrażeniem regularnym. Parametr `{nazwa}` obejmuje niepusty fragment bez `/`. Pierwsza pasująca trasa dostarcza atrybuty żądania, a kontroler jest pobierany z kontenera. Brak dopasowania, także dla niewłaściwej metody, powoduje `NotFoundException`.

`src/Cart/Http/CartController.php`, `CartController::cartId()`, używa nagłówka `X-Cart-Id`; przy jego braku generuje 16 znaków szesnastkowych z ośmiu losowych bajtów. Udane odpowiedzi koszyka i checkoutu zwracają ten identyfikator w nagłówku.

`CartService::show()` i `addItem()` korzystają z `getOrCreate()`: nowy koszyk istnieje początkowo tylko w pamięci. Dodanie produktu zapisuje go, sam odczyt nie. Zmiana ilości, usunięcie, przypisanie promocji i checkout wymagają zapisanego koszyka (`src/Cart/Application/CartService.php`, odpowiednie metody; `src/Cart/Infrastructure/FileCartRepository.php`, `FileCartRepository::getOrCreate()`).

Po zmianie koszyk jest zapisywany, a następnie kontroler oblicza sumy odpowiedzi przez `CartController::cartResponse()` i `CartService::totals()`. Wycena nie jest zapisywana w pliku koszyka (`src/Cart/Http/CartController.php`; `src/Cart/Application/CartService.php`; `src/Cart/Infrastructure/FileCartRepository.php`, `save()`).

Checkout przebiega w następującej kolejności (`src/Cart/Application/CheckoutService.php`, `CheckoutService::checkout()`):

1. Odczyt koszyka i odrzucenie pustego.
2. Obliczenie aktualnej wyceny.
3. `Cart::markCheckedOut()` i zapis zamkniętego koszyka.
4. Utworzenie zamówienia przez `OrderFactory::fromCart()`.
5. Wysłanie `CartCheckedOut` zawierającego koszyk i zamówienie.
6. Zwrócenie zamówienia po zakończeniu listenerów.

`src/Shared/EventDispatcher.php`, `EventDispatcher::dispatch()`, obsługuje dokładną klasę zdarzenia, zachowuje kolejność rejestracji i nie przechwytuje wyjątków listenerów. `src/Cart/Event/ReserveStockListener.php`, `ReserveStockListener::__invoke()`, zmniejsza zapasy, po czym `src/Cart/Event/LogCheckoutListener.php`, `LogCheckoutListener::__invoke()`, dopisuje czas, identyfikatory zamówienia i koszyka oraz końcową kwotę w groszach do `var/checkout.log`.

## Reguły biznesowe

`src/Cart/Domain/CartStatus.php`, `CartStatus`, definiuje `open` i `checked_out`. `src/Cart/Domain/Cart.php`, `Cart::assertOpen()`, blokuje dodanie, zmianę ilości, usunięcie, przypisanie promocji i ponowne zamknięcie koszyka po checkoutcie. Odczyt i wycena zamkniętego koszyka pozostają dostępne.

`Cart::assertQuantity()` wymaga ilości co najmniej 1. `addProduct()` sumuje nową ilość z istniejącą; `changeQuantity()` ustawia ilość docelową. Obie metody porównują ją ze stanem przekazanego produktu przez `assertInStock()`. Zmiana nieistniejącej pozycji zgłasza `InvalidQuantity`; usunięcie nieistniejącej pozycji jest bezskuteczne. Ilość zero nie oznacza usunięcia (`src/Cart/Domain/Cart.php`).

Pozycja przechowuje nazwę i cenę produktu. `CartItem::withQuantity()` zachowuje te wartości, ale ponowne `Cart::addProduct()` zastępuje pozycję aktualną nazwą i ceną katalogową dla całej skumulowanej ilości. Sama zmiana katalogu nie aktualizuje zapisanych pozycji (`src/Cart/Domain/CartItem.php`; `src/Cart/Domain/Cart.php`).

`src/Cart/Pricing/InMemoryPromoCodeRepository.php`, `InMemoryPromoCodeRepository::__construct()` i `find()`, udostępnia `WELCOME10` z rabatem 10% oraz `SUMMER20` z rabatem 20%. Wyszukiwanie ignoruje wielkość liter, lecz nie usuwa spacji. `CartService::applyPromoCode()` sprawdza kod przed odczytem koszyka i zapisuje go wielkimi literami. Koszyk ma jeden kod, a następne przypisanie go zastępuje (`src/Cart/Application/CartService.php`; `src/Cart/Domain/Cart.php`, `applyPromoCode()`).

`src/Cart/Pricing/PromoCodeDiscount.php`, `PromoCodeDiscount::discountFor()`, przy nieobecnym lub nierozpoznanym zapisanym kodzie zwraca zero. `src/Cart/Pricing/BulkDiscount.php`, `BulkDiscount::discountFor()`, przy wartości pozycji co najmniej 50 000 groszy przyznaje 5%.

Oba rabaty liczone są niezależnie od tej samej wartości pozycji przed rabatami. Kolejność konfiguracji to kod, potem rabat ilościowy, lecz drugi rabat nie jest naliczany od pomniejszonej podstawy. `PricingCalculator::calculate()` sumuje rabaty i ogranicza ich łączną kwotę do wartości pozycji (`src/Cart/Pricing/PricingCalculator.php`; `config/services.php`).

`src/Cart/Pricing/ShippingCalculator.php`, `ShippingCalculator::costFor()`, nalicza dostawę od kwoty po rabatach: zero przy kwocie równej zero lub co najmniej 20 000 groszy, w pozostałych przypadkach 1500 groszy. Rabat może więc obniżyć podstawę poniżej progu darmowej dostawy. `PricingCalculator::calculate()` zwraca wartość pozycji minus rabat plus dostawę. Pusty koszyk ma zerowe sumy, ale checkout jest zabroniony (`src/Cart/Application/CheckoutService.php`, `checkout()`).

Kontrola zapasów zachodzi przy dodawaniu i zmianie ilości, bez rezerwacji. Checkout nie sprawdza ponownie dostępności. Listener pobiera aktualny produkt i zapisuje `max(0, stock − quantity)`, zamiast odrzucać niedobór (`src/Cart/Domain/Cart.php`, `assertInStock()`; `src/Cart/Event/ReserveStockListener.php`, `__invoke()`).

`src/Shared/Money.php`, `Money`, przechowuje całkowite grosze i domyślną walutę PLN. `percent()` używa `intdiv(amount * percent, 100)`, co dla nieujemnych kwot obcina ułamek grosza; każdy rabat jest obcinany oddzielnie. Dodawanie, odejmowanie i porównanie progowe wymagają zgodnej waluty; `min()` jej nie sprawdza. Konstruktor nie waliduje nieujemności. Repozytoria odtwarzają ceny jako PLN, a wycena i dostawa korzystają także z domyślnych kwot PLN, więc kod nie zapewnia pełnej obsługi wielu walut.

## Dane i API

Trasy definiuje `config/routes.php`; obsługę realizują `src/Catalog/Http/ProductController.php` i `src/Cart/Http/CartController.php`:

| Metoda i ścieżka | Wejście | Obsługa i sukces |
|---|---|---|
| `GET /products` | Brak | `ProductController::list()`: 200, obiekt `products` z listą |
| `GET /products/{id}` | Identyfikator w trasie | `ProductController::show()`: 200, produkt |
| `GET /cart` | `X-Cart-Id` opcjonalny | `CartController::show()`: 200, koszyk |
| `POST /cart/items` | `productId`, `quantity` | `addItem()`: 201, koszyk |
| `PATCH /cart/items/{productId}` | `quantity` | `changeQuantity()`: 200, koszyk |
| `DELETE /cart/items/{productId}` | Identyfikator w trasie | `removeItem()`: 200, koszyk |
| `POST /cart/promo` | `code` | `applyPromo()`: 200, koszyk |
| `POST /cart/checkout` | Identyfikator koszyka | `checkout()`: 201, zamówienie |

`CartController::addItem()` domyślnie przyjmuje pusty `productId` i ilość 1; `changeQuantity()` domyślnie ilość 0; `applyPromo()` domyślnie pusty kod. Kontroler rzutuje identyfikatory i kod na tekst, ilości na `int`; nie stosuje osobnej walidacji schematu (`src/Cart/Http/CartController.php`).

Produkt ma `id`, `name`, `price`, `stock` (`src/Catalog/Product.php`, `Product::toArray()`). Koszyk zawiera `id`, `status`, `promoCode`, `items`, `totals`; pozycja: `productId`, `name`, `unitPrice`, `quantity`, `lineTotal` (`CartController::cartResponse()`; `src/Cart/Domain/CartItem.php`, `toArray()`). Sumy to `subtotal`, `discount`, `shipping`, `total` (`src/Cart/Pricing/CartTotals.php`, `toArray()`). Każda kwota ma `amount`, `currency`, `formatted`, np. zapis z przecinkiem dziesiętnym (`src/Shared/Money.php`, `toArray()`).

Zamówienie zawiera `id`, `cartId`, `items`, `totals`, `createdAt` w formacie `c`. Identyfikator ma prefiks `ORD-` i osiem wielkich znaków szesnastkowych; fabryka nie weryfikuje samodzielnie statusu koszyka (`src/Order/Order.php`, `toArray()`; `src/Order/OrderFactory.php`, `fromCart()`).

`src/Kernel.php`, `Kernel::handle()`, zwraca JSON `{"error": ...}`: 404 dla `NotFoundException`, 422 dla pozostałych `DomainException`, 500 z ogólnym komunikatem dla innych przechwyconych wyjątków. Brak produktu i koszyka reprezentują `ProductNotFound::withId()` oraz `CartNotFound::withId()` (`src/Catalog/ProductNotFound.php`; `src/Cart/Domain/Exception/CartNotFound.php`). Błędy ilości, zapasów, pustego lub zamkniętego koszyka i kodu promocji dziedziczą po `DomainException` w odpowiednich plikach `src/Cart/Domain/Exception/` oraz `src/Cart/Pricing/InvalidPromoCode.php`.

`FileCartRepository::save()` tworzy `var/carts` i zapisuje osobne JSON-y ze statusem, promocją i pozycjami; cena jednostkowa jest liczbą groszy bez waluty. `get()` odtwarza je przez `Cart::restore()`, omijające walidację domenową. `path()` usuwa z identyfikatora znaki poza literami ASCII, cyframi, `_` i `-`, co może skierować różne identyfikatory do tego samego pliku (`src/Cart/Infrastructure/FileCartRepository.php`; `src/Cart/Domain/Cart.php`).

`JsonProductRepository::load()` wybiera cały `var/products.json`, jeśli istnieje, w przeciwnym razie `data/products.json`. `save()` przepisuje pełną listę do pliku roboczego, bez tworzenia katalogu. Dane startowe zawierają pięć produktów: `p-100` kubek 2999 groszy/50 sztuk, `p-101` notes 1500/120, `p-102` długopis 599/300, `p-103` plecak 17900/15, `p-104` lampkę 8900/2 (`src/Catalog/JsonProductRepository.php`; `data/products.json`).

## Praca z projektem

Z `composer.json` wynikają: PHP >=8.3, instalacja autoloadera przez `composer install`, `composer serve` uruchamiające `php -S localhost:8080 -t public` oraz `composer test` wywołujące `php tests/run.php`. Implementacji testów nie dołączono; nie potwierdzono ich wyników.

Typowe miejsca zmian to: trasy w `config/routes.php`, zależności i kolejność listenerów w `config/services.php`, operacje koszyka w `CartService` i `Cart`, wycena w klasach `src/Cart/Pricing/`, format odpowiedzi w kontrolerach i metodach `toArray()`. Zmiana progów lub rabatów wpływa zarówno na odpowiedzi koszyka, jak i checkout, ponieważ oba używają `PricingCalculator::calculate()`.

Zapis danych zmienia się w `FileCartRepository` i `JsonProductRepository`; skutki checkoutu w listenerach. Edycja `data/products.json` nie zmienia odczytu katalogu, gdy istnieje kopia robocza (`src/Catalog/JsonProductRepository.php`, `load()`).

## Ograniczenia

Mapa potwierdza strukturę, nie zachowanie nieudostępnionych implementacji. Nie dostarczono testów, konfiguracji środowiskowej ani sekretów, zawartości `vendor/`, danych roboczych `var/` i implementacji generatora wykluczeń. Nie można ustalić pełnej listy pomijanych plików ani aktualnych zapisanych koszyków i zapasów.

`src/Payment/PaymentGateway.php`, `PaymentGateway::charge()`, jest wyłącznie interfejsem: brak implementacji, rejestracji i wywołania w checkoutcie. `src/Auth/ApiTokenProvider.php`, `ApiTokenProvider::token()`, zawiera demonstracyjny dostawca wartości; brak jego użycia w routingu i usługach. Dostarczony przepływ nie realizuje uwierzytelniania.

Brak repozytorium zamówień i endpointu ich odczytu; `CheckoutService::checkout()` tworzy obiekt, przekazuje go listenerom i zwraca klientowi. Zapis logu nie jest zapisem pełnego zamówienia.

Repozytoria nie stosują blokad, a checkout nie ma transakcji ani cofania zapisów. Wyjątek listenera może przerwać dalszą obsługę po zapisaniu zamkniętego koszyka i części zmian magazynowych. Wyniki `file_put_contents()` nie są sprawdzane, więc ostrzeżenie lub nieudany zapis nie musi oznaczać odpowiedzi 500 (`FileCartRepository::save()`, `JsonProductRepository::save()`, `LogCheckoutListener::__invoke()`). Ładowanie konfiguracji usług i tras odbywa się poza blokiem przechwytującym wyjątki routingu w `Kernel`; nie wszystkie błędy uruchomienia są więc objęte opisanym formatem odpowiedzi.
