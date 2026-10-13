<?php

declare(strict_types=1);

namespace App\Cart\Domain\Exception;

use App\Shared\Exception\DomainException;

final class InsufficientStock extends DomainException
{
}
