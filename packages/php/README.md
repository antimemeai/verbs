# Verbs for PHP

Prepared Composer identity: `antimemeai/verbs`; not registered on Packagist.
PHP 8.1 or newer. The root composer.json lets Packagist index the existing
personal repository. No runtime dependencies beyond PHP.

```php
use Antimemeai\Verbs\Constraint;
$retries = Constraint::check('bounded retries', 3, fn($n) => $n >= 1 && $n <= 5);
```

The synchronous predicate runs once. Only boolean true passes; failure throws
Violation with its constraint name. Predicate exceptions propagate. Checks
apply at call time; later mutation can invalidate them. Values stay out of
errors. PHP objects preserve identity; PHP arrays follow normal value semantics.
Run `composer test` or `php packages/php/tests/check.php` from the repository root.
The experimental API is MIT licensed.
