/// A synchronous predicate rejected a value, identified by constraint name.
class Violation implements Exception {
  final String constraint;

  Violation(this.constraint);

  @override
  String toString() => 'constraint violated: $constraint';
}

/// Evaluate [predicate] once and return the original [value] on success.
///
/// Throws [Violation] on rejection; predicate exceptions propagate.
/// Later mutation can invalidate a successful check.
T check<T>(String name, T value, bool Function(T) predicate) {
  if (!predicate(value)) throw Violation(name);
  return value;
}
