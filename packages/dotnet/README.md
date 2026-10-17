# Verbs for .NET

Prepared NuGet identity: `Verbs`; not published. Targets .NET Standard 2.0 for
use from C#, F#, and other compatible .NET languages. No runtime package
dependencies beyond the framework.

```csharp
using Verbs;
var retries = Constraint.Check("bounded retries", 3, n => n >= 1 && n <= 5);
```

The synchronous predicate runs once. Success returns the original value;
rejection throws Violation with its Constraint property. Predicate exceptions
propagate. Checks apply at call time; later mutation can invalidate them.
Reference types preserve identity; value types follow normal .NET semantics.
Values stay out of errors. The 0.1.0 API is experimental and MIT licensed.

With a .NET 10 SDK, run `dotnet run --project tests/Check.csproj` and
`dotnet pack Verbs.csproj --configuration Release --output dist` here.
