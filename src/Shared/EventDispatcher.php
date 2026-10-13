<?php

declare(strict_types=1);

namespace App\Shared;

/**
 * Synchroniczny dispatcher zdarzeń. Listener to callable przyjmujący obiekt zdarzenia.
 * Listenery wywołujemy w kolejności rejestracji (patrz config/services.php).
 */
final class EventDispatcher
{
    /** @var array<class-string, list<callable>> */
    private array $listeners = [];

    /** @param class-string $eventClass */
    public function listen(string $eventClass, callable $listener): void
    {
        $this->listeners[$eventClass][] = $listener;
    }

    public function dispatch(object $event): void
    {
        foreach ($this->listeners[$event::class] ?? [] as $listener) {
            $listener($event);
        }
    }
}
