<?php
declare(strict_types=1);

namespace Antimemeai\Verbs;

/** A predicate rejected a value. The value is omitted from the error. */
final class Violation extends \InvalidArgumentException
{
    public function __construct(public readonly string $constraint)
    {
        parent::__construct('constraint violated: ' . $constraint);
    }
}
