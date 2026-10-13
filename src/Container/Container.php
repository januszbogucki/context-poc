<?php

declare(strict_types=1);

namespace App\Container;

use Closure;
use RuntimeException;

/**
 * Prosty kontener DI: fabryki rejestrujemy w config/services.php, instancje są współdzielone.
 */
final class Container
{
    /** @var array<string, Closure(self): object> */
    private array $factories = [];

    /** @var array<string, object> */
    private array $instances = [];

    /** @param Closure(self): object $factory */
    public function set(string $id, Closure $factory): void
    {
        $this->factories[$id] = $factory;
        unset($this->instances[$id]);
    }

    /**
     * @template T of object
     * @param class-string<T> $id
     * @return T
     */
    public function get(string $id): object
    {
        if (!isset($this->instances[$id])) {
            if (!isset($this->factories[$id])) {
                throw new RuntimeException("Service not registered: {$id}");
            }
            $this->instances[$id] = ($this->factories[$id])($this);
        }

        return $this->instances[$id];
    }
}
