using System;
using Verbs;

static class CheckContract
{
    static void Expect(bool condition)
    {
        if (!condition) throw new Exception("contract test failed");
    }

    static void Main()
    {
        for (int n = -10; n <= 10; n++)
        {
            try
            {
                int result = Constraint.Check("bounded", n, v => v >= 1 && v <= 5);
                Expect(n >= 1 && n <= 5 && result == n);
            }
            catch (Violation error)
            {
                Expect(n < 1 || n > 5);
                Expect(error.Constraint == "bounded");
                Expect(error.Message == "constraint violated: bounded");
            }
        }
        object value = new object();
        int calls = 0;
        object resultObject = Constraint.Check("same", value, v => { calls++; return true; });
        Expect(Object.ReferenceEquals(value, resultObject) && calls == 1);
        var sentinel = new InvalidOperationException("predicate failed");
        try
        {
            Constraint.Check("broken", 0, v => { throw sentinel; });
            throw new Exception("predicate error was swallowed");
        }
        catch (InvalidOperationException error)
        {
            Expect(Object.ReferenceEquals(error, sentinel));
        }
        Console.WriteLine(".NET contract checks passed");
    }
}
