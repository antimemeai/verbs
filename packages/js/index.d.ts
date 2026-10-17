/** A named predicate rejected a value. Values are omitted from the error. */
export declare class Violation extends Error {
  readonly constraint: string;
  constructor(constraint: string);
}

/** Evaluate a synchronous predicate once and return the original value. */
export declare function check<T>(
  name: string,
  value: T,
  predicate: (value: T) => boolean,
): T;
