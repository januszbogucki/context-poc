<?php

declare(strict_types=1);

namespace App\Catalog;

use App\Shared\Money;

/**
 * Produkty z pliku JSON. Dane startowe leżą w data/products.json (tylko do odczytu).
 * Zmiany (np. stan magazynu po zamówieniu) zapisujemy do kopii roboczej var/products.json,
 * która ma pierwszeństwo przy odczycie.
 */
final class JsonProductRepository implements ProductRepository
{
    public function __construct(
        private readonly string $seedFile,
        private readonly string $workingFile,
    ) {
    }

    public function all(): array
    {
        return array_values($this->load());
    }

    public function get(string $id): Product
    {
        return $this->load()[$id] ?? throw ProductNotFound::withId($id);
    }

    public function save(Product $product): void
    {
        $products = $this->load();
        $products[$product->id] = $product;

        $rows = array_map(static fn (Product $p) => [
            'id' => $p->id,
            'name' => $p->name,
            'price' => $p->price->amount,
            'stock' => $p->stock,
        ], array_values($products));

        file_put_contents($this->workingFile, json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }

    /** @return array<string, Product> */
    private function load(): array
    {
        $file = is_file($this->workingFile) ? $this->workingFile : $this->seedFile;
        $rows = json_decode((string) file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);

        $products = [];
        foreach ($rows as $row) {
            $products[$row['id']] = new Product($row['id'], $row['name'], new Money($row['price']), $row['stock']);
        }

        return $products;
    }
}
