<?php

declare(strict_types=1);

namespace App\Cart\Event;

/** Dopisuje linię do pliku logu po każdym zamówieniu. */
final class LogCheckoutListener
{
    public function __construct(private readonly string $logFile)
    {
    }

    public function __invoke(CartCheckedOut $event): void
    {
        $line = sprintf(
            "%s order=%s cart=%s total=%d\n",
            date('c'),
            $event->order->id,
            $event->cart->id,
            $event->order->totals->total->amount,
        );
        file_put_contents($this->logFile, $line, FILE_APPEND);
    }
}
