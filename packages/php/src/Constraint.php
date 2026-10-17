<?php
declare(strict_types=1);

namespace Antimemeai\Verbs;

final class Constraint
{
    /**
     * Evaluate a synchronous predicate once; only boolean true passes.
     * Predicate exceptions propagate. Later mutation can invalidate the check.
     * @template T
     * @param T $value
     * @param callable(T): bool $predicate
     * @return T
     */
    public static function check(string $name, mixed $value, callable $predicate): mixed
    {
        if ($predicate($value) !== true) {
            throw new Violation($name);
        }
        return $value;
    }
}
