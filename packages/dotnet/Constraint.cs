using System;

namespace Verbs
{
    /// <summary>A predicate rejected a value; the value is omitted from the error.</summary>
    public sealed class Violation : ArgumentException
    {
        /// <summary>The caller-supplied constraint name.</summary>
        public string Constraint { get; }

        /// <summary>Create a named violation.</summary>
        public Violation(string constraint) : base("constraint violated: " + constraint)
        {
            Constraint = constraint;
        }
    }

    /// <summary>Explicit, named synchronous constraints.</summary>
    public static class Constraint
    {
        /// <summary>
        /// Evaluate the predicate once and return the original value on success.
        /// Predicate exceptions propagate. Later mutation can invalidate a check.
        /// </summary>
        public static T Check<T>(string name, T value, Func<T, bool> predicate)
        {
            if (!predicate(value)) throw new Violation(name);
            return value;
        }
    }
}
