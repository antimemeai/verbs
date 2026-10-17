//! Explicit, named runtime constraints.
//!
//! ```
//! let retries = verbs::check("bounded retries", 3, |n| (1..=5).contains(n))?;
//! assert_eq!(retries, 3);
//! # Ok::<(), verbs::Violation>(())
//! ```
//!
//! A successful check describes the value at check time. It does not preserve
//! the constraint after mutation or prove the predicate itself correct.

use std::fmt;

/// A predicate rejected a value. Values are deliberately omitted from errors.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Violation {
    /// The caller-supplied constraint name.
    pub constraint: &'static str,
}

impl fmt::Display for Violation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "constraint violated: {}", self.constraint)
    }
}

impl std::error::Error for Violation {}

/// Evaluate `predicate` once and return the original value or a named violation.
///
/// Panics from the predicate propagate to the caller.
pub fn check<T>(
    name: &'static str,
    value: T,
    predicate: impl FnOnce(&T) -> bool,
) -> Result<T, Violation> {
    if predicate(&value) {
        Ok(value)
    } else {
        Err(Violation { constraint: name })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_exactly_the_allowed_range() {
        for n in -10..=10 {
            match check("bounded", n, |n| (1..=5).contains(n)) {
                Ok(value) => {
                    assert!((1..=5).contains(&n));
                    assert_eq!(value, n);
                }
                Err(error) => {
                    assert!(!(1..=5).contains(&n));
                    assert_eq!(error.constraint, "bounded");
                    assert_eq!(error.to_string(), "constraint violated: bounded");
                }
            }
        }
    }

    #[test]
    fn returns_original_allocation_and_evaluates_once() {
        let value = Box::new(7);
        let pointer = (&*value) as *const i32;
        let mut calls = 0;
        let checked = check("positive", value, |v| {
            calls += 1;
            **v > 0
        })
        .unwrap();
        assert_eq!(calls, 1);
        assert_eq!((&*checked) as *const i32, pointer);
    }

    #[test]
    fn does_not_convert_predicate_panics_into_violations() {
        let panic = std::panic::catch_unwind(|| {
            check("broken predicate", (), |_| panic!("predicate failed"))
        })
        .unwrap_err();
        assert_eq!(panic.downcast_ref::<&str>(), Some(&"predicate failed"));
    }
}
