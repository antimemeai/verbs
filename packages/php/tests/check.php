<?php
declare(strict_types=1);

require __DIR__ . '/../src/Violation.php';
require __DIR__ . '/../src/Constraint.php';

use Antimemeai\Verbs\Constraint;
use Antimemeai\Verbs\Violation;

function expect(bool $condition): void
{
    if (!$condition) {
        throw new RuntimeException('contract test failed');
    }
}

foreach (range(-10, 10) as $n) {
    try {
        $result = Constraint::check('bounded', $n, fn($n) => $n >= 1 && $n <= 5);
        expect($n >= 1 && $n <= 5 && $result === $n);
    } catch (Violation $error) {
        expect($n < 1 || $n > 5);
        expect($error->constraint === 'bounded');
        expect($error->getMessage() === 'constraint violated: bounded');
    }
}
$value = new stdClass();
$calls = 0;
$result = Constraint::check('same', $value, function ($v) use (&$calls): bool {
    ++$calls;
    return true;
});
expect($result === $value && $calls === 1);
$sentinel = new RuntimeException('predicate failed');
try {
    Constraint::check('broken', 0, function ($v) use ($sentinel): bool { throw $sentinel; });
    throw new LogicException('predicate error was swallowed');
} catch (RuntimeException $error) {
    expect($error === $sentinel);
}
foreach ([1, 'true', [], new stdClass(), null] as $invalid) {
    try {
        Constraint::check('boolean', 0, fn($v) => $invalid);
        throw new LogicException('non-boolean accepted');
    } catch (Violation $error) {
        expect($error->constraint === 'boolean');
    }
}
echo "PHP contract checks passed\n";
