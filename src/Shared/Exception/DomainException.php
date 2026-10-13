<?php

declare(strict_types=1);

namespace App\Shared\Exception;

use RuntimeException;

/** Bazowy wyjątek błędów biznesowych. Kernel mapuje go na HTTP 422. */
class DomainException extends RuntimeException
{
}
