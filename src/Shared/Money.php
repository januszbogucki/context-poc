<?php

declare(strict_types=1);

namespace App\Shared;

use InvalidArgumentException;

/**
 * Kwota w groszach (int), żeby uniknąć błędów zaokrągleń float. Obiekt niemutowalny.
 */
final readonly class Money
{
    public function __construct(
        public int $amount,
        public string $currency = 'PLN',
    ) {
    }

    public static function zero(string $currency = 'PLN'): self
    {
        return new self(0, $currency);
    }

    public function add(self $other): self
    {
        $this->assertSameCurrency($other);
        return new self($this->amount + $other->amount, $this->currency);
    }

    public function subtract(self $other): self
    {
        $this->assertSameCurrency($other);
        return new self($this->amount - $other->amount, $this->currency);
    }

    public function multiply(int $factor): self
    {
        return new self($this->amount * $factor, $this->currency);
    }

    /** Procent kwoty, zaokrąglony w dół do pełnego grosza. */
    public function percent(int $percent): self
    {
        return new self(intdiv($this->amount * $percent, 100), $this->currency);
    }

    public function isZero(): bool
    {
        return $this->amount === 0;
    }

    public function isGreaterThanOrEqual(self $other): bool
    {
        $this->assertSameCurrency($other);
        return $this->amount >= $other->amount;
    }

    public function min(self $other): self
    {
        return $this->amount <= $other->amount ? $this : $other;
    }

    /** @return array{amount: int, currency: string, formatted: string} */
    public function toArray(): array
    {
        return [
            'amount' => $this->amount,
            'currency' => $this->currency,
            'formatted' => sprintf('%d,%02d %s', intdiv($this->amount, 100), $this->amount % 100, $this->currency),
        ];
    }

    private function assertSameCurrency(self $other): void
    {
        if ($this->currency !== $other->currency) {
            throw new InvalidArgumentException("Currency mismatch: {$this->currency} vs {$other->currency}");
        }
    }
}
