# Verbs for Dart

Prepared pub.dev identity: `verbs`; not published. Dart 3 or newer, including
Flutter applications. No runtime or test dependencies beyond the SDK.

```dart
import 'package:verbs/verbs.dart';
final retries = check('bounded retries', 3, (n) => n >= 1 && n <= 5);
```

The synchronous predicate runs once. Success returns the original value;
rejection throws Violation with its constraint name. Predicate exceptions
propagate. Checks apply at call time; later mutation can invalidate them.
Values stay out of errors. The 0.1.0 API is experimental and MIT licensed.

Run `dart pub get`, `dart analyze`, and `dart run test/check.dart` here.
`dart pub publish --dry-run` checks the package without claiming its name.
