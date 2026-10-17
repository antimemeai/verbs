# verbs — Design Brief

> **Repository note (2026-10-17):** The operator wrote this brief with web
> Claude as an orientation aid, not a directive. Nothing in it is settled,
> including §1. It is kept verbatim below as the founding input to research and
> design; journal/2026-10-17-operator-decisions.md records where discussion has
> moved past it.

**Audience:** an implementing agent (Claude Code) working with Blob.
**Status:** design synthesized from a review of an earlier ChatGPT inventory plus follow-up decisions. Decisions in §1 are settled; everything in §12 is open. Items marked **VERIFY** are claims made from memory that must be checked against the actual toolchain before building on them.

---

## 0. Glossary

| Term | Meaning |
|---|---|
| **verbs** | This project: structural typing, invariant discovery, and edit-local verification feedback for C++ (first) and Rust (later). |
| **Blackbird** | Blob's own coding agent. Primary consumer of verbs feedback. Owns agent planning and tool orchestration. |
| **Becoming** (working name) | Separate project: literate specification, modeling, mathematical claims, general specification language. verbs may reference its artifacts by ID; it must never require them. |
| **constraingent** | Separate layer for broader agent integration/affordances. verbs owns the machine API and delta format; Blackbird/constraingent own *when* to call it. |
| **vlib** | The verbs C++ type library (bounded, refined, kinds, enums, typestate, capabilities, FSMs). |
| **verbs-facts** | LibTooling binary that extracts program facts into the derived cache. |
| **delta daemon** | Persistent process that returns revision-tagged diagnostic deltas after each edit. |

---

## 1. Settled decisions

1. **No cross-language parity.** Each language gets the best realization of each theme given how that language works. Docs state per-language guarantees honestly. Never pretend Rust and C++ offer identical guarantees.
2. **C++ first.** Target: **Clang, C++23**. Build a meaningful set of C++ phases, then catch Rust up.
3. **Type work is in scope and early.** vlib is the vocabulary that the lints' fix-its rewrite *toward*, and the mechanism that removes preservation obligations (§2). It is foundational, not optional.
4. **"Chits" (signed verification attestations) are deleted.** What survives is content-addressed, regenerable cache entries for preservation verdicts (§7). No signing, no attestation service.
5. **No database service.** State is split into three tiers: source, committed text, disposable cache (§7).
6. **Verification backends: minimal.** No nine-backend portfolio. C++ starts with in-compiler mechanisms (type system, Clang analyses, `consteval` checking) plus tests/trace validation. Add external checkers only when a real property demands one.

---

## 2. The spine: invariants, transformations, preservation

verbs is organized around one model with three objects:

- **Invariant**: a predicate over a subject (value, type, object, relation between fields, protocol, system), with a **scope** where it must hold.
- **Transformation**: anything that can change a subject or the program: functions, methods, ctors/dtors, assignment, FSM transitions, ingress (deserialization/FFI), **exception unwinding**, **moves**, escapes (leaked references), **edits**, **refactors**.
- **Preservation judgment**: whether transformation T preserves invariant I (`preserves | establishes | weakens | breaks | unknown | assumed`), via which mechanism, at which revision.

Two senses of the concept are both required:

1. **Invariant as conserved quantity.** A predicate preserved by the dynamics. Covers bounded/refined types, typestate, FSM safety, class invariants.
2. **Invariance under transformation.** A judgment that doesn't change under a transformation (cf. Reynolds parametricity). Covers:
   - newtype/kind discipline;
   - refactor safety;
   - **the incremental engine**: a cached result is valid exactly when it is invariant under the edit δ.

### How every theme maps onto the spine

| Theme | Operation on (Invariant, Transformations, Preservation) |
|---|---|
| Bounded / finite / refined types | Encode I in the representation → preservation trivial, or checked once at ingress |
| Typestate, capabilities | Restrict which transformations are *available* at a point |
| Linter / discovery | Hypothesize I (static + dynamic evidence); find unguarded T |
| FSM checking | Prove the reachable closure T* preserves I (inductive invariant) |
| Trace validation | Empirically observe preservation |
| Incremental engine | Decide which preservation judgments are invariant under edit δ |
| Refactor analysis | Check behavior invariant under the refactor transformation |

### Core metric

The core metric is **open preservation obligations.** Moving an invariant up the mechanism ladder deletes rows from the obligation set:

> observation → checked-at-ingress → typecheck → unrepresentable

Invariants enforced by representation never appear in the gap query. That is the quantitative form of "make invalid states unrepresentable."

### C++-specific weakening/leak paths (first-class transformation kinds)

- **Exception unwinding.** Abrahams' exception-safety guarantees *are* preservation statements. The basic guarantee means invariants are preserved under unwinding; the strong guarantee means state is unchanged.
- **Moved-from state.** "Valid but unspecified" is a declared *weakening*. Model it as a separate invariant with scope `moved_from`.
- **Leaking accessors.** A public member returning a non-const ref/pointer to a field that participates in an invariant.
- **Escape hatches.** `mutable`, `const_cast`, `friend`, `reinterpret_cast`, public data members in invariant-bearing classes.
- **Scope semantics.**
  - Class invariants hold at *visible states* (between public calls), per Meyer's design by contract and Boogie/Spec# ownership.
  - TSA `GUARDED_BY` = scope "while holding capability C".

### Guardrails on the spine

- **`predicate` is a small canonical vocabulary**, not arbitrary logic: ranges, finite sets, linear equalities between fields, state membership, capability-held. Anything richer lives in Becoming and is referenced by ID.
- **Strength is a partial order, not a ladder of ints.** A bounded model check and checked construction aren't comparable. Store the *set* of mechanisms per invariant; consumers decide what is strong enough. Examples of consumers:
  - lint suppression;
  - Blackbird trust;
  - `[[assume]]` eligibility.
- **`[[assume]]` gating.** A wrong `[[assume]]` is UB. Only invariants with mechanism `representation` or `typecheck` may ever be emitted as `[[assume]]`.

---

## 3. C++ realization map

| Theme | C++ realization | Guarantee tier |
|---|---|---|
| Bounded/range | NTTP `Bounded<Lo,Hi>` with type-level range propagation and range-selected storage | Compile time (arithmetic); construction (runtime ingress) |
| Finite domains | `VERBS_ENUM` (owned enum declaration + complete value array) + `-Werror=switch-enum` | Compile time |
| Kinds/newtypes | Tagged strong typedefs `Id<UserTag>` vs `Id<OrderTag>`, no implicit conversions | Compile time |
| Refinements | `Refined<T, Pred>` with named predicate types, `std::expected` factory | Construction |
| Typestate (2-state) | Clang `-Wconsumed`: `consumable`, `callable_when`, `set_typestate`, `return_typestate` | Compile time; intraprocedural; only consumed/unconsumed/unknown |
| Typestate (rich) | Phantom state template param; transitions `&&`-qualified, return `T<Next>` | Compile time; **cannot** prevent use of moved-from handle (state this in docs) |
| Capabilities | Clang Thread Safety Analysis, repurposed (`capability` works on any type) | Compile time; scope-based |
| Finite FSM checking | `consteval` BFS + `static_assert` over declared transition table | Compile time; small state spaces |
| Protocol correspondence | Trace validation in tests against the declared table | Empirical |

### Consumer warning flags

```
-Wthread-safety -Wthread-safety-beta -Wconsumed -Werror=switch-enum
-Wconversion -Wsign-conversion
```

`-Wconversion` / `-Wsign-conversion` will be noisy on legacy code. Roll them out as per-directory opt-ins.

### C++23 features to use

- `std::expected` for refinement failures.
- `static operator()` for stateless named predicates.
- Deducing `this` to reduce typestate boilerplate.
- `if consteval` for single-path compile-time/runtime checks.
- `[[assume]]`, gated as in §2.

**VERIFY:** deducing `this` needs Clang ≥ 18 and `[[assume]]` needs Clang ≥ 19 (from memory). Check `clang++ --version` and pin.

---

## 4. vlib sketches

These are starting points, not final code. Each needs tests and compile-fail tests (static_assert / concept-rejection cases).

### 4.1 Bounded

Design points:

- **Range propagation chooses non-overflowing storage.** Result ranges are computed at compile time, so the runtime computation (done in `int64_t`) cannot overflow when the bounds fit.
- **Bound overflow is a compile error for free.** If the *bounds* overflow `int64_t`, constant evaluation fails, because UB in a constant expression is ill-formed. Add an `__int128` tier later if needed.
- **No raw-int ingress.** Values enter only through `lit<V>()` (compile-time checked) or `make(v)` (runtime checked). Narrowing is impossible; widening is implicit.

```cpp
#pragma once
#include <algorithm>
#include <concepts>
#include <cstdint>
#include <optional>
#include <type_traits>
#include <utility>

namespace verbs {
namespace detail {
template<std::int64_t Lo, std::int64_t Hi>
using storage_for =
  std::conditional_t<(Lo >= INT8_MIN  && Hi <= INT8_MAX),  std::int8_t,
  std::conditional_t<(Lo >= INT16_MIN && Hi <= INT16_MAX), std::int16_t,
  std::conditional_t<(Lo >= INT32_MIN && Hi <= INT32_MAX), std::int32_t, std::int64_t>>>;

consteval std::int64_t min4(std::int64_t a, std::int64_t b, std::int64_t c, std::int64_t d) {
  return std::min({a, b, c, d});
}
consteval std::int64_t max4(std::int64_t a, std::int64_t b, std::int64_t c, std::int64_t d) {
  return std::max({a, b, c, d});
}

struct access {  // single trusted construction path across specializations
  template<class B> static constexpr B make(typename B::rep v) noexcept { return B(v); }
};
}  // namespace detail

template<std::int64_t Lo, std::int64_t Hi>
class Bounded {
  static_assert(Lo <= Hi, "empty domain");
  friend struct detail::access;
public:
  using rep = detail::storage_for<Lo, Hi>;
  static constexpr std::int64_t min = Lo, max = Hi;

  template<std::int64_t V> requires (Lo <= V && V <= Hi)
  static consteval Bounded lit() { return Bounded(static_cast<rep>(V)); }

  template<std::integral T>
  static constexpr std::optional<Bounded> make(T v) noexcept {   // the only runtime check
    if (std::cmp_less(v, Lo) || std::cmp_greater(v, Hi)) return std::nullopt;
    return Bounded(static_cast<rep>(v));
  }

  template<std::int64_t L2, std::int64_t H2> requires (L2 <= Lo && Hi <= H2)
  constexpr operator Bounded<L2, H2>() const noexcept {          // widening only
    using W = Bounded<L2, H2>;
    return detail::access::make<W>(static_cast<typename W::rep>(v_));
  }

  constexpr std::int64_t get() const noexcept { return v_; }

  template<std::int64_t A, std::int64_t B>
  friend constexpr auto operator+(Bounded x, Bounded<A, B> y) noexcept {
    using R = Bounded<Lo + A, Hi + B>;                            // bound overflow => compile error
    return detail::access::make<R>(static_cast<typename R::rep>(std::int64_t{x.v_} + y.get()));
  }

  template<std::int64_t A, std::int64_t B>
  friend constexpr auto operator-(Bounded x, Bounded<A, B> y) noexcept {
    using R = Bounded<Lo - B, Hi - A>;
    return detail::access::make<R>(static_cast<typename R::rep>(std::int64_t{x.v_} - y.get()));
  }

  template<std::int64_t A, std::int64_t B>
  friend constexpr auto operator*(Bounded x, Bounded<A, B> y) noexcept {
    using R = Bounded<detail::min4(Lo * A, Lo * B, Hi * A, Hi * B),
                      detail::max4(Lo * A, Lo * B, Hi * A, Hi * B)>;
    return detail::access::make<R>(static_cast<typename R::rep>(std::int64_t{x.v_} * y.get()));
  }

  // Division: require the divisor range to exclude zero, statically.
  // template<std::int64_t A, std::int64_t B> requires (!(A <= 0 && 0 <= B)) ...

  template<std::integral T> Bounded(T) = delete;                  // no raw-int ingress
private:
  constexpr explicit Bounded(rep v) noexcept : v_(v) {}
  rep v_;
};
}  // namespace verbs
```

### 4.2 Refined

Rules:

- **Named predicate types only.** Ban lambda predicates (C++20 lets you write `Refined<int, [](int x){...}>`). Each lambda is a distinct type, so identical-looking refinements won't interconvert, and predicates lose stable identity.
- **Every predicate carries an `id`.** The `Violation` it produces maps back to an `invariant` row.
- **No mutable access.** Only `const` `get()` is exposed, so the refinement is preserved.

```cpp
#include <expected>
#include <string_view>

namespace verbs {
struct Violation { std::string_view predicate_id; };

template<class T, class Pred>
  requires std::predicate<Pred, const T&>
class Refined {
public:
  static constexpr std::expected<Refined, Violation> make(T v) {
    if (!Pred{}(v)) return std::unexpected(Violation{Pred::id});
    return Refined(std::move(v));
  }
  constexpr const T& get() const noexcept { return v_; }          // no mutable access
private:
  constexpr explicit Refined(T v) : v_(std::move(v)) {}
  T v_;
};

struct Positive {
  static constexpr std::string_view id = "positive";
  static constexpr bool operator()(std::int64_t x) noexcept { return x > 0; }
};
}  // namespace verbs
```

### 4.3 Finite domains: `VERBS_ENUM`

Do **not** rely on `magic_enum` for exhaustiveness. Its default ±128 reflection range silently misses values outside it. verbs owns the enum declaration so that three consumers get an exact, complete domain:

- the FSM checker;
- the enum-candidate fix-it;
- the `verbs-facts` matcher.

Intended expansion of `VERBS_ENUM(Mode, Idle, Armed, Firing)`:

```cpp
enum class Mode : std::uint8_t { Idle, Armed, Firing };
inline constexpr std::array<Mode, 3> verbs_values_Mode{Mode::Idle, Mode::Armed, Mode::Firing};
inline constexpr std::array<std::string_view, 3> verbs_names_Mode{"Idle", "Armed", "Firing"};
// + a verbs::enum_traits<Mode> specialization exposing values/names/size
```

### 4.4 Kinds (strong typedefs)

```cpp
template<class Tag, class Rep = std::uint64_t>
class Id {
public:
  constexpr explicit Id(Rep v) noexcept : v_(v) {}
  constexpr Rep get() const noexcept { return v_; }
  friend constexpr bool operator==(Id, Id) = default;
  friend constexpr auto operator<=>(Id, Id) = default;
private:
  Rep v_;
};
struct UserTag; struct OrderTag;
using UserId = Id<UserTag>; using OrderId = Id<OrderTag>;   // not interconvertible
```

### 4.5 Typestate

**Two-state** (use-after-close/move) via Clang consumed analysis:

```cpp
class [[clang::consumable(unconsumed)]] Conn {
public:
  [[clang::return_typestate(unconsumed)]] explicit Conn(Endpoint);
  [[clang::callable_when("unconsumed")]] void send(Frame);
  [[clang::set_typestate(consumed)]] void close();
};
```

**Rich** via phantom state:

```cpp
struct Idle {}; struct Armed {};
template<class S> class Door {
public:
  Door<Armed> arm() && requires std::same_as<S, Idle>;
  // moved-from Door<Idle> remains usable in C++ — documented limitation
};
```

### 4.6 Capabilities via Thread Safety Analysis

```cpp
struct __attribute__((capability("authority"))) LedgerWrite {};
extern LedgerWrite ledger_write;

void acquire_ledger() __attribute__((acquire_capability(ledger_write)));
void release_ledger() __attribute__((release_capability(ledger_write)));
void post_entry(Entry e) __attribute__((requires_capability(ledger_write)));
// -Wthread-safety: calling post_entry without holding ledger_write is a compile error
```

Wrap these attributes in `VERBS_*` macros.

### 4.7 Compile-time FSM checking

The same function runs under `static_assert` for the verdict, and at runtime in a test binary to print a counterexample (`static_assert` cannot emit a trace).

```cpp
template<class M>
constexpr bool check_invariant(auto on_violation) {
  std::array<bool, M::N> seen{};
  std::array<typename M::State, M::N> q{};
  std::size_t h = 0, t = 0;
  q[t++] = M::init; seen[M::index(M::init)] = true;
  while (h < t) {
    auto s = q[h++];
    if (!M::invariant(s)) { on_violation(s); return false; }
    for (auto e : M::events)
      if (auto n = M::step(s, e); n && !seen[M::index(*n)]) {
        seen[M::index(*n)] = true; q[t++] = *n;
      }
  }
  return true;
}
static_assert(check_invariant<DoorModel>([](auto) {}));
```

Extension: store parent pointers for full trace reconstruction at runtime.

**VERIFY:**
- Feasible state-space size under `-fconstexpr-steps` (estimate 10⁴–10⁵ states, unbenchmarked).
- Whether the stdlib in use supports transient `constexpr std::vector`; if so, it can replace the fixed arrays.

Above the feasible size, export the table to TLA+/TLC.

**Trace validation** closes the model↔implementation gap:

1. The implementation emits transition events under test.
2. Observed traces are checked against the declared table.

---

## 5. Delta daemon (edit-local feedback)

Integration point: **Blackbird's edit-tool boundary.** An edit's result carries the diagnostic delta inline. File watching is a secondary path for humans.

### Tiers

| Tier | Mechanism | Latency |
|---|---|---|
| 0 | clangd over LSP (preamble caching, open files) | sub-second |
| 1 | verbs clang-tidy checks on affected TUs only | seconds |
| 2 | `ctest -R` filtered to targets depending on changed TUs | varies |

### Tier details

- **Speculative patch analysis is free.** `textDocument/didChange` takes in-memory content, so the daemon can send hypothetical text without touching disk.
- **Revision tagging and supersession are free.** `publishDiagnostics` carries `version`; drop anything older than the file's current version. **VERIFY** clangd populates `version` when `versionSupport` is advertised.
- **Affected TUs.** Use `ninja -C build -t deps` for header→TU reverse dependencies.
- **Tier-1 command:**
  ```
  run-clang-tidy -p build -load ./libVerbsTidy.so -checks='-*,verbs-*' <tus>
  ```
- **Plugin constraints.**
  - **VERIFY** the clang-tidy `-load` plugin flag exists in the pinned LLVM.
  - clangd does **not** load out-of-tree tidy plugins. Getting verbs checks at tier 0 requires a custom clangd build with the module linked in.
  - **Pin the LLVM major version.** The plugin ABI is per-release.

### Python prototype

The production daemon may move to C++ later.

```python
import asyncio, json, itertools, os, subprocess
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass(frozen=True)
class DiagKey:                     # key on scope/code/message, NOT line numbers (lines shift)
    uri: str; code: str; msg: str; scope: str   # scope = enclosing symbol via documentSymbol (TODO)

@dataclass
class FileState:
    version: int = 0
    diags: set = field(default_factory=set)

class Clangd:
    def __init__(self, compile_commands_dir: str):
        self.cc_dir, self.ids, self.pending = compile_commands_dir, itertools.count(1), {}
        self.files: dict[str, FileState] = {}
        self.waiters: dict[tuple[str, int], asyncio.Future] = {}

    async def start(self):
        self.p = await asyncio.create_subprocess_exec(
            "clangd", f"--compile-commands-dir={self.cc_dir}", "--background-index",
            "--clang-tidy", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        asyncio.create_task(self._reader())
        await self.request("initialize", {"processId": None, "rootUri": None,
            "capabilities": {"textDocument": {"publishDiagnostics": {"versionSupport": True}}}})
        await self.notify("initialized", {})

    async def _send(self, msg):
        body = json.dumps(msg).encode()
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        await self.p.stdin.drain()

    async def request(self, method, params):
        i = next(self.ids); fut = asyncio.get_running_loop().create_future()
        self.pending[i] = fut
        await self._send({"jsonrpc": "2.0", "id": i, "method": method, "params": params})
        return await fut

    async def notify(self, method, params):
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _reader(self):
        while True:
            hdr = await self.p.stdout.readuntil(b"\r\n\r\n")
            n = int(hdr.split(b"Content-Length:")[1].split(b"\r\n")[0])
            msg = json.loads(await self.p.stdout.readexactly(n))
            if "id" in msg and msg["id"] in self.pending:
                self.pending.pop(msg["id"]).set_result(msg.get("result"))
            elif msg.get("method") == "textDocument/publishDiagnostics":
                self._on_diags(msg["params"])

    def _on_diags(self, p):
        uri, ver = p["uri"], p.get("version")
        fs = self.files.get(uri)
        if fs is None or ver is None or ver < fs.version:
            return                                               # superseded: drop
        new = {DiagKey(uri, str(d.get("code", "")), d["message"], d.get("source", ""))
               for d in p["diagnostics"]}
        delta = {"rev": ver, "added": new - fs.diags, "resolved": fs.diags - new}
        fs.diags = new
        if (w := self.waiters.pop((uri, ver), None)):
            w.set_result(delta)

    async def edit(self, uri: str, text: str, lang="cpp") -> dict:
        """Called from Blackbird's edit-tool boundary. Returns a diagnostic delta for this revision."""
        fs = self.files.setdefault(uri, FileState())
        fs.version += 1
        fut = asyncio.get_running_loop().create_future()
        self.waiters[(uri, fs.version)] = fut
        if fs.version == 1:
            await self.notify("textDocument/didOpen", {"textDocument": {
                "uri": uri, "languageId": lang, "version": 1, "text": text}})
        else:
            await self.notify("textDocument/didChange", {
                "textDocument": {"uri": uri, "version": fs.version},
                "contentChanges": [{"text": text}]})
        return await asyncio.wait_for(fut, timeout=30)


def header_to_tus(build_dir: str) -> dict[str, set[str]]:
    """Reverse deps from Ninja: file -> set of primary TU sources that include it.
    Assumes the first listed dep of each target is its primary source (true for Clang -MD deps)."""
    out = subprocess.run(["ninja", "-C", build_dir, "-t", "deps"],
                         capture_output=True, text=True, check=True).stdout
    rev, first = defaultdict(set), None
    for line in out.splitlines():
        if not line.strip():
            first = None; continue
        if not line[0].isspace():
            first = None; continue                               # target header line
        dep = os.path.normpath(os.path.join(build_dir, line.strip()))
        if first is None:
            first = dep
        rev[dep].add(first)
    return rev
```

### Delta output shape (target)

Concise and machine-readable. Expand on demand.

```
VERBS r184
  +1 structural  -3 resolved  2 invariants preserved  1 obligation invalidated
  src/protocol.cpp  Door::mode
    finite discriminator widened to uint32_t; previously excluded states now representable
    suggest: keep VERBS_ENUM or record open_domain in .verbs/decisions.jsonl
```

---

## 6. Facts and lints

### verbs-facts

- LibTooling binary sharing one AST-matcher library with the clang-tidy module (`verbs-*` checks).
- **Dataflow:** use Clang's FlowSensitive dataflow framework (the one behind `bugprone-unchecked-optional-access`) for escape/boundary questions, not the path-sensitive Static Analyzer.
- **Dynamic evidence (Daikon-style):** a candidate-driven Clang `Rewriter` pass that instruments *only* fields the static lints flagged, in test builds, logging observed value sets. Static plus dynamic evidence = confidence.

### Lints

First wave (C2):

1. **`verbs-enum-candidate`**: integers/strings compared or assigned against a small literal set across ≥2 functions. Confidence drops to `hypothesis` if the value escapes into arithmetic/FFI/unknown.
2. **`verbs-kind-discovery`**: Lackwit-style usage-based type inference. Primitives of the same C++ type whose dataflow never mixes are distinct kinds; suggest `Id<Tag>`. Highest-value lint.
3. **`verbs-bool-cluster`**: sets of bool flags whose valid combinations imply an undeclared sum type/state.
4. **`verbs-repeated-guard`**: the same predicate checked by multiple consumers. Suggest establishing it at construction (`Refined`/`Bounded`).

Second wave (C3, enabled by the spine):

5. **`verbs-invariant-leak`**: public accessor returning non-const ref/pointer to an invariant-bearing field; also `mutable`/`const_cast`/public fields in invariant-bearing classes.
6. **`verbs-unwind-preservation`**: a member function mutates invariant-bearing state, then calls something that can throw, with no rollback (violates the basic guarantee).

All lints emit **code actions toward vlib types**, not just warnings. The linter must distinguish observation from hypothesis in its output.

### Enum-candidate query

This runs over the derived cache. Fact table shapes are illustrative.

```sql
-- assign(rev, place, fn, const_val) ; compare(rev, place, fn, const_val, op) ; escape(rev, place, kind)
WITH lit_domain AS (
  SELECT place,
         COUNT(DISTINCT const_val) AS n_vals,
         COUNT(DISTINCT fn)        AS n_fns
  FROM (SELECT place, fn, const_val FROM assign  WHERE rev = :rev
        UNION ALL
        SELECT place, fn, const_val FROM compare WHERE rev = :rev AND op IN ('eq','ne'))
  GROUP BY place
),
tainted AS (
  SELECT DISTINCT place FROM escape
  WHERE rev = :rev AND kind IN ('arith','ffi','unknown')
)
SELECT d.place, d.n_vals, d.n_fns,
       CASE WHEN t.place IS NULL THEN 'high' ELSE 'hypothesis' END AS confidence
FROM lit_domain d LEFT JOIN tainted t USING (place)
WHERE d.n_vals BETWEEN 2 AND 16
  AND d.n_fns >= 2
ORDER BY confidence, d.n_fns DESC;
```

---

## 7. State: three tiers, no database service

| Tier | Authored by | Holds | Format | Lifetime |
|---|---|---|---|---|
| 1. Source | Code | Declared invariants: vlib types; `[[clang::annotate("verbs:inv ...")]]` for non-type-encoded ones | C++ | Permanent |
| 2. Decisions | Humans/agents | Verdicts the code can't express | `.verbs/decisions.jsonl`, committed | Shrinks as invariants get encoded |
| 3. Cache | Tools | Facts, mutates, preservation verdicts, observations, dependency hashes | In-memory first; SQLite in `build/` later | Disposable |

**Hard rule:** the cache must be fully regenerable from source + `.verbs/`. A migration is just delete-and-rebuild.

### `[[clang::annotate]]` usage

- Needs no plugin and doesn't trip `-Wunknown-attributes`.
- Appears in the AST as `AnnotateAttr` on fields, types and functions.
- Example: `[[clang::annotate("verbs:inv eq(len(a),len(b)) scope=visible_state")]]`.

### Decisions ledger

`.verbs/decisions.jsonl` holds one line per (subject, predicate). Verdicts:

- **`rejected`**: the hypothesis is false (e.g. "this int is not a 3-value enum"). Exists primarily so the linter doesn't re-propose it every run, and so Blackbird doesn't re-litigate it or "accept" it to silence the warning.
- **`open_domain`**: deliberately unconstrained, with rationale. Still lint ingress boundaries.
- **`accepted_pending`**: the invariant holds and will be encoded. Delete the line once a vlib type/annotation carries it.

```json
{"subject":"c:@S@Door@FI@mode","qname":"Door::mode","predicate":"in{0,1,3}","verdict":"rejected","author":"human","rationale":"wire protocol reserves 3-7 for future modes","evidence":{"const_vals":[0,1,3],"cmp_sites":4,"escapes":["arith"]},"evidence_fp":"sha256:…","date":"2026-10-17"}
```

Ledger rules:

- **Key on USR + qualified name.** USRs change on rename, so fall back to `qname`. If both miss, report the entry as an **orphan**; never drop it silently.
- **Evidence fingerprint.** Stay silent while the evidence is unchanged. Resurface a `rejected`/`open_domain` hypothesis when evidence shifts materially:
  - new constant values appear;
  - comparison sites grow by ≥3 or ≥50%;
  - an escape kind disappears (e.g. arithmetic use removed).
- **Agent-authored entries surface separately in diffs/PR review** (`author: "agent"`). This is the Goodhart defense: agents must not be able to silently suppress diagnostics.

### Cache open/rebuild

```python
import sqlite3, pathlib

SCHEMA_VERSION = 1
SCHEMA = pathlib.Path(__file__).with_name("schema.sql")

def open_cache(build_dir: str) -> sqlite3.Connection:
    path = pathlib.Path(build_dir) / "verbs.cache.db"
    db = sqlite3.connect(path)
    if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        db.close(); path.unlink(missing_ok=True)          # migration == rebuild
        db = sqlite3.connect(path)
        db.executescript(SCHEMA.read_text())
        db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        db.commit()
    db.execute("PRAGMA journal_mode = WAL")               # daemon writes, CLI reads concurrently
    return db
```

It's acceptable to start with plain Python dicts in the daemon and the gap/invalidation logic as functions. The schema below doubles as the design of those structures. Move to SQLite when ad-hoc querying is wanted.

---

## 8. Cache schema (`schema.sql`)

```sql
CREATE TABLE subject (
  id   INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('value','type','object','relation','protocol','system')),
  ref  TEXT NOT NULL,               -- Clang USR, or sorted field-USR set for 'relation'
  UNIQUE (kind, ref)
);

CREATE TABLE invariant (
  id         INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL REFERENCES subject(id),
  predicate  TEXT NOT NULL,         -- canonical: 'range(0,10)', 'in{Idle,Armed}', 'eq(len(a),len(b))'
  scope      TEXT NOT NULL CHECK (scope IN ('always','visible_state','guarded','after_point','moved_from','region')),
  scope_ref  TEXT,                  -- capability USR for 'guarded', program point for 'after_point'
  origin     TEXT NOT NULL CHECK (origin IN ('declared','inferred_static','inferred_dynamic','suggested')),
  status     TEXT NOT NULL CHECK (status IN ('accepted','hypothesis','rejected','open_domain')),
  author     TEXT NOT NULL CHECK (author IN ('human','agent','tool')),
  rationale  TEXT
);

CREATE TABLE mechanism (            -- how an invariant is made to hold; a set per invariant (partial order)
  invariant_id INTEGER NOT NULL REFERENCES invariant(id),
  kind  TEXT NOT NULL CHECK (kind IN ('representation','typecheck','construction','analysis',
                                      'proof','model_check','observation','assertion')),
  site  TEXT NOT NULL,
  bound TEXT,                       -- state/unwind bound; NULL = exhaustive
  rev   TEXT NOT NULL
);

CREATE TABLE transformation (
  id   INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('function','method','ctor','dtor','assign','transition',
                                     'ingress','unwind','move','escape','edit','refactor')),
  ref  TEXT NOT NULL,
  UNIQUE (kind, ref)
);

CREATE TABLE mutates (              -- from verbs-facts: which transformations can change which subjects
  transformation_id INTEGER NOT NULL REFERENCES transformation(id),
  subject_id        INTEGER NOT NULL REFERENCES subject(id),
  PRIMARY KEY (transformation_id, subject_id)
);

CREATE TABLE preservation (
  id                INTEGER PRIMARY KEY,
  invariant_id      INTEGER NOT NULL REFERENCES invariant(id),
  transformation_id INTEGER NOT NULL REFERENCES transformation(id),
  verdict TEXT NOT NULL CHECK (verdict IN ('preserves','establishes','weakens','breaks','unknown','assumed')),
  via     TEXT NOT NULL,            -- mechanism kind that produced the verdict
  rev     TEXT NOT NULL,
  UNIQUE (invariant_id, transformation_id, rev)
);

CREATE TABLE preservation_dep (     -- what a verdict rests on; the edit-invariance key
  preservation_id INTEGER NOT NULL REFERENCES preservation(id),
  symbol          TEXT NOT NULL,
  content_hash    TEXT NOT NULL     -- hash of normalized AST of symbol at that rev (insensitive to comments/format)
);
```

**Preservation gaps.** Accepted invariants with a mutator lacking a solid verdict, C++ leak paths first:

```sql
SELECT i.id, i.predicate, i.scope, t.kind, t.ref,
       COALESCE(p.verdict, 'missing') AS verdict
FROM invariant i
JOIN mutates m        ON m.subject_id = i.subject_id
JOIN transformation t ON t.id = m.transformation_id
LEFT JOIN preservation p
       ON p.invariant_id = i.id AND p.transformation_id = t.id AND p.rev = :rev
WHERE i.status = 'accepted'
  AND NOT EXISTS (SELECT 1 FROM mechanism x
                  WHERE x.invariant_id = i.id AND x.kind = 'representation' AND x.rev = :rev)
  AND (p.id IS NULL OR p.verdict IN ('unknown','assumed','weakens','breaks'))
ORDER BY (t.kind IN ('unwind','move','escape','ingress')) DESC, i.id;
```

**Edit invalidation.** Judgments no longer known to be invariant under the edit. `changed(symbol, new_hash)` is a temp table filled by the daemon.

```sql
SELECT DISTINCT i.id, i.predicate, t.ref AS transformation, p.verdict, p.via
FROM preservation p
JOIN preservation_dep d ON d.preservation_id = p.id
JOIN changed c          ON c.symbol = d.symbol AND c.new_hash <> d.content_hash
JOIN invariant i        ON i.id = p.invariant_id
JOIN transformation t   ON t.id = p.transformation_id
WHERE p.rev = :prev_rev;
```

Invalidation is conservative: any changed dependency invalidates. Never reuse a verdict optimistically.

---

## 9. Phases (C++ first)

| Phase | Deliverables | Notes |
|---|---|---|
| **C0** | Spine docs; `schema.sql`; `.verbs/decisions.jsonl` format + loader; cache open/rebuild; toolchain pin (LLVM major, stdlib) | Small. Locks vocabulary. |
| **C1** | **vlib core:** `Bounded`, `Refined`, `Id<Tag>`, `VERBS_ENUM`, Consumed/TSA macros, phantom typestate. **Delta daemon:** clangd tier 0, tidy tier 1, ctest tier 2, Blackbird edit-hook integration | Run in parallel. Compile-fail tests for vlib. |
| **C2** | `verbs-facts` + lints 1–4 with code actions targeting vlib; candidate-driven dynamic observation | vlib is the fix-it vocabulary, which is why it comes first. |
| **C3** | Preservation tracking: `mutates`, verdicts, gap + invalidation queries wired into deltas; lints 5–6 | The spine becomes operational. |
| **C4** | FSMs: declared `constexpr` tables, `consteval` checking + runtime counterexample, trace validation, extraction motif suggesting tables from existing code | TLA+ export for large state spaces. |
| **R1+** | Rust catch-up with native realizations: ownership instead of Consumed; ZST tokens instead of TSA; Stateright instead of `consteval` BFS; weaker range propagation until `generic_const_exprs` stabilizes; Dylint for custom lints; rust-analyzer/salsa for incrementality; Kani + bolero when needed; loom/shuttle for concurrency | Shares schema and decisions format. |

---

## 10. Evaluation (kill criterion)

Avoid vanity metrics such as raw state-space reduction. Run one experiment:

1. Take a corpus of real tasks on Blob's C++ repos.
2. Seed defects with mutation testing (**Mull**, LLVM-based C/C++ mutation testing; **VERIFY** fit with the build).
3. Run Blackbird **with and without** verbs.
4. Measure:
   - **edits-to-detection** (repair amplification);
   - **wall-clock-to-detection**;
   - tokens and tool calls;
   - final correctness;
   - **suppressions added** (especially agent-authored);
   - **open preservation obligations** over time.

If verbs doesn't meaningfully move edits-to-detection, stop and rethink.

---

## 11. Do not

- Do not build cross-language parity abstractions.
- Do not implement signing/attestation ("chits").
- Do not adopt a database server. The cache is disposable SQLite or in-memory.
- Do not let `predicate` become a general logic; defer to Becoming.
- Do not use `magic_enum` for exhaustiveness.
- Do not allow lambda predicates in `Refined`.
- Do not emit `[[assume]]` for invariants below `representation`/`typecheck`.
- Do not key diagnostics on line numbers.
- Do not let agent suppressions land silently.
- Do not add external verification backends speculatively.

---

## 12. Open questions

- **Predicate grammar:** the exact canonical vocabulary and its normal form, needed for stable IDs and dedup.
- **Lint inference thresholds:** precision vs recall per lint, and when `hypothesis` findings are shown vs held back.
- **verbs-facts architecture:** standalone LibTooling over `compile_commands.json` vs hooking clangd's index.
- **Dynamic observation:** Clang `Rewriter` source instrumentation vs an LLVM pass.
- **Relation subjects:** identity for multi-field invariants under refactors (field renames, splits).
- **Daemon language:** Python prototype → C++ (same toolchain as vlib) or Rust.
- **Becoming interface:** how verbs references external predicates by ID.
- **Enforcement policy:** advisory by default; how modules opt into hard gates.

---

## 13. Prior art to read

- **Lackwit** — O'Callahan & Jackson, ICSE 1997. Usage-based type inference for abstract types in C.
- **Mining Specifications** — Ammons, Bodík & Larus, POPL 2002. Protocol inference.
- **Daikon** — Ernst et al. Dynamic invariant detection.
- **Design by Contract** (Meyer); **Boogie/Spec# ownership methodology**. Visible-state invariant semantics.
- **Exception-safety guarantees** — Abrahams.
- **Theorems for free / parametricity** — Reynolds, Wadler. Invariance under representation change.
- **TLA+ trace validation** — Cirstea, Kuppe, Merz et al.
- **Clang:** Thread Safety Analysis docs; Consumed analysis attributes; FlowSensitive dataflow framework; LibTooling/AST matchers.
- **Fact stores:** CodeQL, Soufflé, Glean. Shape of the fact model.
- **Mull** — mutation testing for C/C++.
