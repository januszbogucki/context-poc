<?php

declare(strict_types=1);

namespace App\Shared\Exception;

/** Nie znaleziono zasobu. Kernel mapuje go na HTTP 404. */
class NotFoundException extends DomainException
{
}
