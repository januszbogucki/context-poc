<?php

declare(strict_types=1);

namespace App\Cart\Domain;

enum CartStatus: string
{
    case Open = 'open';
    case CheckedOut = 'checked_out';
}
