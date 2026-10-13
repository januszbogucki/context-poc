<?php

declare(strict_types=1);

namespace App\Http;

use App\Container\Container;
use App\Shared\Exception\NotFoundException;

/**
 * Router oparty o wyrażenia regularne. Trasa: metoda + wzorzec ze zmiennymi {nazwa} -> [Kontroler::class, 'metoda'].
 * Kontroler jest pobierany z kontenera.
 */
final class Router
{
    /** @var list<array{method: string, regex: string, handler: array{0: class-string, 1: string}}> */
    private array $routes = [];

    /** @param array{0: class-string, 1: string} $handler */
    public function get(string $pattern, array $handler): void
    {
        $this->add('GET', $pattern, $handler);
    }

    /** @param array{0: class-string, 1: string} $handler */
    public function post(string $pattern, array $handler): void
    {
        $this->add('POST', $pattern, $handler);
    }

    /** @param array{0: class-string, 1: string} $handler */
    public function patch(string $pattern, array $handler): void
    {
        $this->add('PATCH', $pattern, $handler);
    }

    /** @param array{0: class-string, 1: string} $handler */
    public function delete(string $pattern, array $handler): void
    {
        $this->add('DELETE', $pattern, $handler);
    }

    /** @param array{0: class-string, 1: string} $handler */
    private function add(string $method, string $pattern, array $handler): void
    {
        $regex = '#^' . preg_replace('#\{(\w+)\}#', '(?P<$1>[^/]+)', $pattern) . '$#';
        $this->routes[] = ['method' => $method, 'regex' => $regex, 'handler' => $handler];
    }

    public function dispatch(Request $request, Container $container): Response
    {
        foreach ($this->routes as $route) {
            if ($route['method'] !== $request->method) {
                continue;
            }
            if (preg_match($route['regex'], $request->path, $matches) === 1) {
                $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
                [$class, $action] = $route['handler'];

                return $container->get($class)->$action($request->withAttributes($params));
            }
        }

        throw new NotFoundException("Route not found: {$request->method} {$request->path}");
    }
}
