"""Explicit, named synchronous constraints; checked at the time of the call."""

from collections.abc import Callable
from typing import TypeVar

__all__ = ["Violation", "check"]
T = TypeVar("T")


class Violation(ValueError):
    """A predicate rejected a value, identified only by its constraint name."""

    def __init__(self, constraint: str) -> None:
        self.constraint = constraint
        super().__init__(f"constraint violated: {constraint}")


def check(name: str, value: T, predicate: Callable[[T], bool]) -> T:
    """Evaluate once; return the original value only for the boolean True.

    Predicate exceptions propagate. Later mutation can invalidate the constraint.
    """
    if predicate(value) is not True:
        raise Violation(name)
    return value
