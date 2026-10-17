import 'package:verbs/verbs.dart';

void expect(bool condition) {
  if (!condition) throw StateError('contract test failed');
}

void main() {
  for (var n = -10; n <= 10; n++) {
    try {
      final result = check('bounded', n, (n) => n >= 1 && n <= 5);
      expect(n >= 1 && n <= 5 && result == n);
    } on Violation catch (error) {
      expect(n < 1 || n > 5);
      expect(error.constraint == 'bounded');
      expect(error.toString() == 'constraint violated: bounded');
    }
  }
  final value = <int>[];
  var calls = 0;
  final result = check('same', value, (_) {
    calls++;
    return true;
  });
  expect(identical(value, result) && calls == 1);
  final sentinel = StateError('predicate failed');
  try {
    check('broken', 0, (_) => throw sentinel);
    throw StateError('predicate error was swallowed');
  } catch (error) {
    expect(identical(error, sentinel));
  }
  print('Dart contract checks passed');
}
