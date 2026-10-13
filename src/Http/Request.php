<?php

declare(strict_types=1);

namespace App\Http;

final class Request
{
    /**
     * @param array<string, string> $headers nagłówki z małymi literami w kluczach
     * @param array<string, mixed> $body zdekodowany JSON
     * @param array<string, string> $attributes parametry z trasy, np. {id}
     */
    public function __construct(
        public readonly string $method,
        public readonly string $path,
        public readonly array $headers = [],
        public readonly array $body = [],
        public readonly array $attributes = [],
    ) {
    }

    public static function fromGlobals(): self
    {
        $headers = [];
        foreach ($_SERVER as $key => $value) {
            if (str_starts_with($key, 'HTTP_')) {
                $headers[strtolower(str_replace('_', '-', substr($key, 5)))] = (string) $value;
            }
        }

        $raw = file_get_contents('php://input') ?: '';
        $body = $raw !== '' ? (json_decode($raw, true) ?? []) : [];

        return new self(
            strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET'),
            parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/',
            $headers,
            is_array($body) ? $body : [],
        );
    }

    public function header(string $name): ?string
    {
        return $this->headers[strtolower($name)] ?? null;
    }

    public function attribute(string $name): string
    {
        return $this->attributes[$name] ?? '';
    }

    /** @param array<string, string> $attributes */
    public function withAttributes(array $attributes): self
    {
        return new self($this->method, $this->path, $this->headers, $this->body, $attributes);
    }
}
