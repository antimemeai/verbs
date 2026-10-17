/** A named predicate rejected a value. */
export class Violation extends Error {
  /** @param {string} constraint */
  constructor(constraint) {
    super(`constraint violated: ${constraint}`);
    this.name = "Violation";
    this.constraint = constraint;
  }
}

/**
 * Evaluate a synchronous predicate once, returning the original value on success.
 * Only the boolean true passes; promises and other truthy values are rejected.
 * @template T
 * @param {string} name
 * @param {T} value
 * @param {(value: T) => boolean} predicate
 * @returns {T}
 */
export function check(name, value, predicate) {
  if (predicate(value) !== true) throw new Violation(name);
  return value;
}
