# Core literature: the verbs spine and its themes

Lane report, 2026-10-17. This lane acquired and read the foundational
literature behind verbs-design-brief.md (the brief), and looked for work that
challenges or supersedes it. The brief is orientation, not settled design.

The 44 PDFs named here sit in `papers/`, which Git ignores. Their SHA-256
hashes are at the end. The extracted text was read from
`pdftotext` output. **Read depth** says what was read:

- **full:** the whole paper;
- **core:** the abstract, the method, and the results or limitations sections;
- **abstract+:** the abstract plus targeted searches of the text.

The synthesis at the end is the part to read first.

---

## 1. Usage-based type and abstraction inference

### Lackwit
O'Callahan, R., Jackson, D. "Lackwit: A Program Understanding Tool Based on
Type Inference." ICSE 1997. Source:
https://homes.cs.washington.edu/~mernst/teaching/6.883/readings/ocallahan-icse97.pdf
File: `ocallahan-jackson-1997-lackwit-icse.pdf`. Read depth: full.

**What it does:**
- Ignores C's declared types.
- Runs Hindley–Milner (algorithm W) over a translated C program, with tagged type
  constructors. Two values that must share a representation unify.
- Function signatures are polymorphic, which gives context sensitivity.
- Casts are treated as the identity. Type errors are reported and analysis
  continues.
- Read/written/allocated/freed flags ride as extra type parameters. These find
  never-read locations and leaks.

**Measured:** on a 17 KLOC program, building the database took 274 s and
queries were instant.

**The key negative result:** "a set of integer variables that are grouped
together by chains of arithmetic operations; queries that hit this set (about
65% of all queries on integer-valued components) will probably produce too much
information to be useful."

**Implication for verbs:**
- **Supports the brief:** `verbs-kind-discovery` has sound prior art, and its
  per-module fact generation fits a batch extractor.
- **Against the brief as written:** unification over arithmetic collapses most
  integers into one kind. The lint needs an explicit *interaction definition*
  (see Guo below). The brief does not mention this parameter.

### Dynamic inference of abstract types (DynComp)
Guo, P. J., Perkins, J. H., McCamant, S., Ernst, M. D. "Dynamic Inference of
Abstract Types." ISSTA 2006, pp. 255–265, doi:10.1145/1146238.1146268. Source:
https://pg.ucsd.edu/publications/dynamic-inference-of-abstract-types_ISSTA-2006.pdf
File: `guo-2006-dynamic-inference-abstract-types-issta.pdf`. Read depth: core.

**What it does:** the same goal as Lackwit, done dynamically. Every runtime
value gets a tag, and interacting values unify through union-find. The authors
implemented it for x86 binaries (C/C++) and for Java. It ships inside Daikon.

**Four interaction definitions, from finest to coarsest:**
1. *dataflow* only;
2. dataflow plus comparisons;
3. *units*: `+`, `-` and comparisons unify, while `*` and `/` do not;
4. *arithmetic* (the default): all arithmetic and bitwise operations unify, and
   shifts unify only the shifted operand.

`&&`, `||` and `?:` never unify.

**Results:**
- DynComp beat Lackwit on bzip2, flex and others. Lackwit merged 15 globals into
  one type because argv elements are indistinguishable statically. Guo argues
  that "almost any static analysis" shares this limit.
- A dynamic result checked afterwards by a static type check is sound.

**Implication for verbs:**
- The brief's static Lackwit-style lint should take the interaction definition
  as a first-class choice. *Units* mode matches "kinds" best.
- The dynamic route already exists for C/C++.
- The brief's "static + dynamic evidence = confidence" has a stronger form here:
  dynamic inference proposes the kinds, and the compiler checks them once they
  are written down as `Id<Tag>`.

---

## 2. Invariant and specification mining

### Daikon
Ernst, M. D., Cockrell, J., Griswold, W. G., Notkin, D. "Dynamically
Discovering Likely Program Invariants to Support Program Evolution." IEEE TSE
27(2), 2001. Source: https://homes.cs.washington.edu/~mernst/pubs/invariants-tse2001.pdf
File: `ernst-2001-dynamically-discovering-likely-invariants-tse.pdf`. Read depth: abstract+.

Ernst, M. D., Perkins, J. H., Guo, P. J., McCamant, S., Pacheco, C., Tschantz,
M. S., Xiao, C. "The Daikon system for dynamic detection of likely invariants."
Science of Computer Programming 69 (2007) 35–45, doi:10.1016/j.scico.2007.01.015.
Source: https://homes.cs.washington.edu/~mernst/pubs/daikon-tool-scp2007.pdf
File: `ernst-2007-daikon-system-scp.pdf`. Read depth: full.

**What it does:**
- Generate-and-check over 75 invariant templates, including ranges,
  one-of/small sets, linear relations, ordering, containment and sortedness.
  Templates are instantiated over parameters, pre-state values (`orig`), fields,
  pure-method results and 25 kinds of derived variables.
- Reports a property only if a null-hypothesis test says it is unlikely to hold
  by chance.
- Suppresses implied invariants, and uses abstract types (DynComp) to avoid
  comparing unrelated variables.
- Kvasir instruments C/C++ binaries.
- Object invariants are computed over all public entry and exit points.
- The NASA CTAS work (over 1 MLOC of C/C++) needed Daikon focused on subsets of
  the program.

**Implication for verbs:**
- The brief's dynamic evidence pass reinvents a narrow Daikon. Its "log
  observed value sets" step gives no statistical justification. Daikon's
  null-hypothesis filter is the existing answer to the brief's open question on
  showing versus holding back `hypothesis` findings.
- The brief's canonical vocabulary (ranges, finite sets, linear equalities)
  overlaps Daikon's core templates closely. A shared normal form is attainable.

### Static verification of dynamically detected invariants
Nimmer, J. W., Ernst, M. D. "Static verification of dynamically detected
program invariants: Integrating Daikon and ESC/Java." RV 2001. Source:
https://homes.cs.washington.edu/~mernst/pubs/invariants-verify-rv2001.pdf
File: `nimmer-ernst-2001-static-verification-dynamically-detected-invariants.pdf`. Read depth: abstract+.

The 2007 paper summarizes the results. Of Daikon's properties, over 95% were
provable by ESC/Java (precision), and over 90% of the properties needed for
verification were found (recall).

**Implication:** the propose-dynamically, check-statically pipeline is proven.
The brief's mechanism ladder (observation → checked-at-ingress → typecheck)
matches it, but C++ has no ESC-class checker for the middle step. The real
check is to *encode the invariant as a vlib type and let the compiler reject
violations*.

### Mining Specifications
Ammons, G., Bodík, R., Larus, J. R. "Mining Specifications." POPL 2002,
pp. 4–16, doi:10.1145/503272.503275. Source (Wayback copy of the author PDF):
https://web.archive.org/web/2008id_/http://www.cs.berkeley.edu/~bodik/research/popl02a.pdf
File: `ammons-bodik-larus-2002-mining-specifications-popl.pdf`. Read depth: abstract+.

**What it does:**
1. Trace API interactions.
2. Annotate flow dependences.
3. Extract small "scenarios" over at most k objects.
4. Learn a probabilistic FSA.
5. "Core" it by dropping rarely used edges.

It found real bugs. Its premise is that a debugged program reveals the correct
protocol in its frequent behaviour.

**Implication:** this is the C4 "extraction motif suggesting tables from
existing code" with prior art. The dynamic version is better grounded than the
brief's implied static extraction.

### DIDUCE
Hangal, S., Lam, M. S. "Tracking Down Software Bugs Using Automatic Anomaly
Detection." ICSE 2002. Source: https://cs.fit.edu/~pkc/id/related/hangal-icse02.pdf
File: `hangal-lam-2002-diduce-icse.pdf`. Read depth: abstract+.

DIDUCE starts from the strictest invariant hypothesis and relaxes it on each
violation. The violations themselves are the bug reports.

**Implication:** this is an online alternative to batch Daikon. It fits the
brief's "candidate-driven instrumentation" because it reports the *first
deviation*, which is what an agent needs mid-task.

### Houdini
Flanagan, C., Leino, K. R. M. "Houdini, an Annotation Assistant for ESC/Java."
FME 2001, LNCS 2021, pp. 500–517 (SRC Technical Note 2000-003). Source:
https://ftp.mirrorservice.org/sites/www.bitsavers.org/pdf/dec/tech_reports/SRC-TN-2000-003.pdf
File: `flanagan-leino-2001-houdini-esc-java.pdf`. Read depth: core.

**What it does:**
- Guesses many candidate annotations from heuristics. For each field it
  compares integral fields with each other and with constants, and adds
  `f != null`. It also adds `requires false` to find dead code.
- Runs the checker and removes every refuted candidate.
- Repeats until a fixpoint, which is the *maximal valid subset* of the
  candidates.

The authors say that showing users the *refuted* candidates and why they were
refuted is "the most important aspect of the user interface".

**Implication:** the brief's lints only hypothesize. Houdini is the
already-solved loop: hypothesize, refute, keep the survivors. The `rejected`
verdict in the brief's ledger corresponds to Houdini's refuted set, and
Houdini's UI lesson supports surfacing rejections.

### LLM-era invariant and specification inference

**Pei, K. et al., "Can LLMs Reason about Program Invariants?"**
- Citation: Pei, K., Bieber, D., Shi, K., Sutton, C., Yin, P. ICML 2023.
- Source: https://proceedings.mlr.press/v202/pei23a/pei23a.pdf
- File: `pei-2023-llms-reason-about-program-invariants-icml.pdf`. Read depth: abstract+.
- Finding: statically, an LLM predicts invariants about as well as Daikon given
  five traces.

**Lemur**
- Citation: Wu, H., Barrett, C., Narodytska, N. "Lemur: Integrating LLMs in
  Automated Program Verification." ICLR 2024.
- Source: https://arxiv.org/pdf/2310.04870
- File: `wu-2024-lemur-llm-program-verification-iclr.pdf`. Read depth: abstract+.
- Finding: a calculus, proved sound, in which the LLM proposes sub-goal
  invariants and the reasoner checks them.

**AutoSpec**
- Citation: Wen, C. et al. "Enchanting Program Specification Synthesis by LLMs
  using Static Analysis and Program Verification." CAV 2024.
- Source: https://arxiv.org/pdf/2404.00762
- File: `wen-2024-autospec-specification-synthesis-llm-cav.pdf`. Read depth: abstract+.
- Finding: static-analysis-driven decomposition with validation each round;
  79% of programs verified.

**nl2postcond**
- Citation: Endres, M., Fakhoury, S., Chakraborty, S., Lahiri, S. K. "Can LLMs
  Transform NL Intent into Formal Method Postconditions?" FSE 2024.
- Source: https://arxiv.org/pdf/2310.01831
- File: `endres-2024-nl2postcond-fse.pdf`. Read depth: abstract+.

**ClassInvGen**
- Citation: Sun, C., Agashe, V., Chakraborty, S., Taneja, J., Barrett, C.,
  Dill, D., Qiu, X., Lahiri, S. K. "ClassInvGen: Class Invariant Synthesis
  using LLMs." 2025.
- Source: https://arxiv.org/pdf/2502.18917
- File: `sun-2025-classinvgen-class-invariant-synthesis-llm.pdf`. Read depth: core.
- **Target:** C++. The LLM writes class invariants as *executable pure C++
  `check_invariant` functions* and generates test inputs alongside them.
  Tests prune wrong candidates, and a mutant harness measures completeness.
- **Results:**
  - Beats Daikon and a pure-LLM baseline.
  - Correctness rises from 77% (raw) to 100% after test filtering.
  - Refinement adds 29% more surviving invariants.
  - Case study on Z3 utility classes, including `bdd_manager`.
- **Implication:** this is the closest existing system to the brief's
  discovery-plus-encoding loop, and it is C++.

**Akhond et al., "LLM For Loop Invariant Generation and Fixing: How Far Are We?"**
- Citation: Akhond, M. R., Chakraborty, S., Uddin, G. arXiv:2511.06552 (2025).
- Source: https://arxiv.org/pdf/2511.06552
- File: `akhond-2025-llm-loop-invariant-generation-fixing.pdf`. Read depth: abstract+.
- Finding: up to 78% success at generating invariants, but only 16% at
  *repairing* a wrong one.

**Quokka**
- Citation: Wei, A., Sun, T., Suresh, T., Wu, H., Wang, K., Aiken, A. "Quokka:
  Accelerating Program Verification with LLMs via Invariant Synthesis." COLM 2026.
- Source: https://arxiv.org/pdf/2509.21629
- File: `wei-2026-quokka-llm-invariant-synthesis-colm.pdf`. Read depth: abstract+.
- Finding: validates each candidate directly against the target assertion, on
  866 SV-COMP-derived instances.

**Chen et al., "Beyond Basic Specifications?"**
- Citation: Chen, Z. et al. "A Systematic Study of Logical Constructs in
  LLM-based Specification Generation." arXiv:2602.00715 (2026).
- Source: https://arxiv.org/pdf/2602.00715
- File: `chen-2026-beyond-basic-specifications-llm.pdf`. Read depth: abstract+.

**Implication of the LLM-era results:**
- The generator problem is largely solved by the agent itself. What is scarce is
  a cheap, trustworthy *refuter*, plus a place to record refutations.
- The brief puts discovery inside verbs (Lackwit and Daikon-style lints). The
  literature points to a split: Blackbird proposes candidates, and verbs checks
  them by compiler, test filtering and mutants, then records the verdict.
- LLMs are weak at repairing invariants (16%). So when verbs refutes a
  candidate, the feedback should be a concrete counterexample, not "try again".

---

## 3. Contracts, ownership, and when invariants hold

### Applying design by contract
Meyer, B. "Applying 'Design by Contract'." IEEE Computer 25(10), 1992. Source:
https://se.inf.ethz.ch/~meyer/publications/computer/contract.pdf
File: `meyer-1992-applying-design-by-contract.pdf`. Read depth: abstract+.

This is the source of the class invariant as an implicit pre- and postcondition
of every exported routine.

### The Boogie methodology
Barnett, M., DeLine, R., Fähndrich, M., Leino, K. R. M., Schulte, W.
"Verification of object-oriented programs with invariants." JOT 3(6), 2004,
pp. 27–56. Source: https://www.jot.fm/issues/issue_2004_06/article2.pdf
File: `barnett-2004-verification-oo-programs-invariants-jot.pdf`. Read depth: core.

The paper calls the popular visible-state regime **faulty**. Under that regime
an invariant must hold at public entry and exit, and callers ignore it. The
failure is reentrancy:

> `x := x + 3; P(...); y := 4 * y;` where P calls back into M breaks M's assumption.

Boogie replaces visible states with an explicit `st ∈ {Valid, Invalid}`:
- `pack` checks the invariant and sets the object to Valid;
- `unpack` sets it to Invalid;
- a field may be updated only while the object is Invalid.

**Implication:** the brief says class invariants hold at visible states "per
Meyer's design by contract and Boogie/Spec# ownership". That misattributes
Boogie, which was built to *reject* plain visible-state semantics. Callbacks
and reentrancy are a missing transformation kind in the brief. For C++ they
include virtual calls, observers, `std::function` callbacks, and user code run
from inside a member function.

### Object invariants in dynamic contexts
Leino, K. R. M., Müller, P. "Object Invariants in Dynamic Contexts." ECOOP 2004.
Source: https://microsoft.com/en-us/research/wp-content/uploads/2016/02/specsharp-krml132.pdf
File: `leino-muller-2004-object-invariants-dynamic-contexts-ecoop.pdf`. Read depth: abstract+.

Ownership contexts can be transferred. An object's invariant may depend on
fields of objects it transitively owns.

### A unified framework for object invariants
Drossopoulou, S., Francalanza, A., Müller, P., Summers, A. J. "A Unified
Framework for Verification Techniques for Object Invariants." ECOOP 2008,
pp. 412–437. Source:
https://www.um.edu.mt/library/oar/bitstream/123456789/22907/1/A_Unified_Framework_for_Verification_Techniques_fo.pdf
File: `drossopoulou-2008-unified-framework-object-invariants-ecoop.pdf`. Read depth: core.

**Three challenges for object invariants:**
- call-backs;
- multi-object invariants;
- subclassing.

**Seven parameters on which verification techniques differ:**
1. invariant semantics (which invariants hold when);
2. invariant restrictions;
3. proof obligations;
4. program restrictions;
5. type systems;
6. specification languages;
7. verification logics.

Using the framework, the authors found an unsoundness in a published technique.

**Implication:** the brief's `scope = visible_state` is not one thing. verbs
must say which objects' invariants are assumed at a visible state: the
receiver's, every object's, or owned objects'. It must also say what a
multi-object (`relation`) invariant permits. The brief's preservation-gap query
joins `mutates` on the invariant's subject. That join is sound only under
*stability*: o's invariant can be broken only by modifying o. Multi-object
invariants break stability unless an ownership discipline restores it.

### Semantic collaboration
Polikarpova, N., Tschannen, J., Furia, C. A., Meyer, B. "Flexible Invariants
Through Semantic Collaboration." FM 2014, LNCS 8442, pp. 514–530. Source:
https://arxiv.org/pdf/1311.6329
File: `polikarpova-2014-flexible-invariants-semantic-collaboration-fm.pdf`. Read depth: abstract+.

The paper states stability as the defining property of invariant reasoning,
and handles collaborating objects through explicit subject and observer sets.
It is implemented in AutoProof (Eiffel).

**Implication:** the brief's relation subjects need this kind of explicit
dependency set, or the gap query under-reports.

### VCC and two-state invariants
Cohen, E., Dahlweid, M., Hillebrand, M., Leinenbach, D., Moskal, M., Santen,
T., Schulte, W., Tobies, S. "VCC: A Practical System for Verifying Concurrent
C." TPHOLs 2009, LNCS 5674, pp. 23–42. Source:
https://www.microsoft.com/en-us/research/wp-content/uploads/2009/01/tphol2009.pdf
File: `cohen-2009-vcc-practical-verifying-concurrent-c-tphols.pdf`. Read depth: abstract+.

Cohen, E., Moskal, M., Schulte, W., Tobies, S. "A Practical Verification
Methodology for Concurrent Programs." MSR-TR-2009-2019 (the companion to the
CAV 2010 paper "Local Verification of Global Invariants in Concurrent
Programs"). Source: https://microsoft.com/en-us/research/wp-content/uploads/2009/02/concurrency.pdf
File: `cohen-2009-practical-verification-methodology-concurrent-programs-msr-tr.pdf`. Read depth: abstract+.

VCC uses *two-state* invariants: relations between the state before and after
each update, spanning objects. It checks them modularly, and verified the
Hyper-V hypervisor.

**Implication:** the brief's predicates are single-state only, but much of what
verbs cares about is two-state:
- a counter never decreases;
- a mode moves only along the declared table;
- an ID never changes after construction;
- moved-from is reached only by a move.

A preservation verdict is itself a two-state judgement. The canonical
vocabulary should include `old(x)` relations.

---

## 4. Exception safety

Abrahams, D. "Exception-Safety in Generic Components: Lessons Learned from
Specifying Exception-Safety for the C++ Standard Library." In Generic
Programming, LNCS 1766, 2000, doi:10.1007/3-540-39953-4_6. Read from the Boost
HTML text: https://www.boost.org/doc/libs/1_34_0/more/generic_exception_safety.html
(PDF not acquired). Read depth: core.

**The three guarantees:**
- **Basic:** the component's invariants are preserved *and no resources leak*.
- **Strong:** the operation completes, or the state is exactly as it was before.
- **No-throw.**

Abrahams notes that the basic guarantee is "less useful than it might at first
appear" when there are many valid states.

**Automated testing (Section 7, Abrahams with Matt Arnold):**
1. Put a `ThisCanThrow()` countdown in every operation that is allowed to throw,
   including an instrumented `operator new`.
2. Run the operation under test with the countdown starting at 0, 1, 2 and so
   on. This throws at *every* possible failure point in turn.
3. After each throw, check the invariant, check for leaks, and check strong-mode
   equality.

**Implication:** the brief correctly treats unwinding as a transformation, but
gives `verbs-unwind-preservation` only a static lint. Abrahams's exhaustive
throw injection is the matching oracle: it is exhaustive over failure points
and cheap. It also gives "basic guarantee" a precise meaning that includes
resource leaks, which the brief's predicate vocabulary cannot state.

---

## 5. Parametricity

Reynolds, J. C. "Types, Abstraction and Parametric Polymorphism." Information
Processing 83 (IFIP), pp. 513–523. Source:
https://people.mpi-sws.org/~dreyer/tor/papers/reynolds.pdf
File: `reynolds-1983-types-abstraction-parametric-polymorphism.pdf`.
The file is a scanned image, so the text was read from the page image.
Read depth: abstract+.

Wadler, P. "Theorems for free!" FPCA 1989. Source:
https://people.mpi-sws.org/~dreyer/tor/papers/wadler.pdf
File: `wadler-1989-theorems-for-free.pdf`. Read depth: abstract+.

Reynolds' thesis is that "type structure is a syntactic discipline for
enforcing levels of abstraction". The abstraction theorem gives *representation
independence*: clients of an abstract type cannot observe which representation
is chosen. Free theorems follow from parametric polymorphism.

**Implication: the brief overreaches here.**
- C++ templates are *not parametric*. Specialization, `if constexpr`, `sizeof`,
  type traits, concepts and overloading all inspect the type argument, so free
  theorems do not hold for templates.
- What does carry over is Reynolds' representation independence for *closed*
  types, meaning a private representation with friend-only construction.
  vlib's `Bounded`, `Refined` and `Id` are exactly such types.
- So the claim verbs can make is narrow: changing the representation inside a
  vlib type, such as `Id`'s `Rep` or `Bounded`'s storage tier, cannot change
  client behaviour beyond the interface.
- Calling the incremental cache "parametricity" is a metaphor. The literature
  for the cache is build systems (Section 9).

---

## 6. Typestate and capabilities

### Typestate (Strom and Yemini)
Strom, R. E., Yemini, S. "Typestate: A Programming Language Concept for
Enhancing Software Reliability." IEEE TSE 12(1):157–171, 1986,
doi:10.1109/TSE.1986.6312929. Not acquired; see the shopping list.

### Typestates for objects (Fugue)
DeLine, R., Fähndrich, M. "Typestates for Objects." ECOOP 2004, LNCS 3086,
pp. 465–490. Source: https://www.microsoft.com/en-us/research/wp-content/uploads/2004/06/ecoop04.pdf
File: `deline-fahndrich-2004-typestates-for-objects-ecoop.pdf`. Read depth: abstract+.

- **What it does:** Fugue, for .NET. Each typestate names a predicate over
  fields. Aliasing is handled with `NotAliased` / `MaybeAliased` (from Vault's
  linear types). Subclasses can refine a state's meaning through "frame
  typestates".
- **Key claim:** "Typestates generalize object invariants". Making the state
  explicit at every pre- and postcondition "avoid[s] the problem of defining
  where object invariants must hold".
- **Implication:** the brief's invariant scopes `always`, `visible_state`,
  `moved_from` and `after_point` could be typestates rather than a separate
  axis. In particular, `moved_from` *is* a typestate.

### Typestate-oriented programming
Aldrich, J., Sunshine, J., Saini, D., Sparks, Z. "Typestate-Oriented
Programming." Onward! 2009. Source:
https://www.cs.cmu.edu/~aldrich/papers/onward2009-state.pdf
File: `aldrich-2009-typestate-oriented-programming-onward.pdf`. Read depth: abstract+.

Here states are first-class: each state has its own representation and
methods. Aliasing is controlled by permissions (`unique`, `immutable`,
`shared`). The Plural checker ran on a 30 KLOC case study.

**Implication:** C++ cannot track permissions flow-sensitively. That is why the
brief's phantom typestate leaves moved-from handles usable. The literature
confirms the documented limitation is real rather than an implementation gap.

### Clang Thread Safety Analysis
Hutchins, D., Ballman, A., Sutherland, D. "C/C++ Thread Safety Analysis." SCAM
2014. Source: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/42958.pdf
File: `hutchins-2014-clang-thread-safety-analysis-scam.pdf`. Read depth: core.

**How the analysis works:**
- It is a capability calculus. `CAPABILITY` works on any class.
- It enforces a single-writer / multiple-reader discipline.
- Its annotations are dependently typed on parameters, which it compares by
  lowering expressions to SSA.
- It runs in O(n) because capability sets *must match at join points*.
  Conditionally held capabilities are rejected.

**Stated limitations:**
- no attributes on types (so `vector<int GUARDED_BY(mu)>` is impossible);
- no dependent type parameters;
- no alias analysis;
- negative capabilities are assumed outside their scope, which is unsound.

**Deployment:** on by default at Google, with 140,000+ annotations in 20,000+
files, adopted voluntarily. "Contrary to popular belief, the need for
annotations has not been a liability."

**Implication:**
- **Supports the brief:** repurposing TSA for authority tokens is sound in
  principle.
- **Limits the brief:** a capability must be a *named expression* (for example
  a global `ledger_write`, or a member). Per-object capabilities therefore need
  a member, and "held conditionally" cannot be expressed. These limits belong
  in the per-language guarantee statement the brief promises.

Clang's Consumed analysis has no paper. Its attribute docs are at
https://clang.llvm.org/docs/AttributeReference.html. The toolchain lane owns
the details.

---

## 7. Refinement and bounded types

### Liquid Types
Rondon, P. M., Kawaguchi, M., Jhala, R. "Liquid Types." PLDI 2008. Source:
https://goto.ucsd.edu/~rjhala/liquid/liquid_types.pdf
File: `rondon-2008-liquid-types-pldi.pdf`. Read depth: abstract+.

Liquid Types combine Hindley–Milner with predicate abstraction over a *fixed,
finite set of qualifiers*. Refinements are inferred as conjunctions of
qualifiers by a Houdini-like elimination. Annotation fell from 31% of program
text to under 1%.

**Implication:** this is the theory behind the brief's guardrail that
"`predicate` is a small canonical vocabulary". A fixed qualifier set:
- makes inference decidable and fast;
- gives each refinement a canonical form (a set of qualifier instances);
- answers the brief's open question on stable IDs and deduplication.

### Refinement types tutorial
Jhala, R., Vazou, N. "Refinement Types: A Tutorial." arXiv:2010.07763 (2020).
Source: https://arxiv.org/pdf/2010.07763
File: `jhala-vazou-2020-refinement-types-tutorial.pdf`. Read depth: abstract+ (a reference).

### Flux
Lehmann, N., Geller, A., Vazou, N., Jhala, R. "Flux: Liquid Types for Rust."
PLDI 2023. Source: https://arxiv.org/pdf/2207.04034
File: `lehmann-2023-flux-liquid-types-rust-pldi.pdf`. Read depth: abstract+.

Flux refines Rust types and uses ownership for strong updates. Compared with
Prusti, specifications are half as long, verification is about 10× faster, and
loop-annotation overhead drops from an average of 9% to zero.

**Implication for R1:** Flux is a direct alternative to "weaker range
propagation until `generic_const_exprs` stabilizes". The cost is an SMT
backend, which the brief's minimal-backends rule would have to admit
explicitly.

### RefinedC
Sammler, M., Lepigre, R., Krebbers, R., Memarian, K., Dreyer, D., Garg, D.
"RefinedC: Automating the Foundational Verification of C Code with Refined
Ownership Types." PLDI 2021, doi:10.1145/3453483.3454036. Source:
https://pub.ista.ac.at/~msammler/paper/refinedc.pdf
File: `sammler-2021-refinedc-pldi.pdf`. Read depth: abstract+.

RefinedC adds ownership plus refinement to C, with Coq/Iris proofs.

**Implication:** it shows what full C-family refinement costs. It is a ceiling
reference, not a fit for "minimal backends".

### Wuffs
Wuffs language documentation, "Bounds Checking" note. Source:
https://github.com/google/wuffs/blob/main/doc/note/bounds-checking.md
(fetched 2026-10-17; not a PDF). Read depth: full (the note).

Wuffs works as follows:
- Integer types carry refinements such as `base.u32[..= 100]`.
- Bounds and overflow are proved at compile time by interval arithmetic plus
  explicit *facts* from prior checks.
- `m + n` of two `u8` values stays `u8`, and the compiler must prove the sum
  fits.
- The prover is deliberately "fast (and dumb)", not an SMT solver.

**Implication: a design fork the brief does not discuss.**
- The brief's `Bounded` *widens the result type on every operation*
  (`Bounded<Lo+A, Hi+B>`). Then `sum = sum + x` in a loop cannot typecheck:
  values carried across loop iterations have no representation.
- Wuffs instead *keeps the declared type* and discharges a proof obligation
  using facts.
- In C++, Wuffs' approach would turn into a runtime-checked assignment or a
  saturating or clamping operation. That needs an explicit design decision.

---

## 8. FSM checking and trace validation

### Trace validation against TLA+
Cirstea, H., Kuppe, M. A., Loillier, B., Merz, S. "Validating Traces of
Distributed Programs Against TLA+ Specifications." arXiv:2404.16075 (2024).
Source: https://arxiv.org/pdf/2404.16075
File: `cirstea-2024-validating-traces-tla-specifications.pdf`. Read depth: core.

**What it does:**
- Traces record only *updates* to the specification variables, and may record
  only some of them.
- TLC reconstructs the missing state as a constrained model-checking problem.
- Depth-first search bounded by the trace length beats breadth-first search.

It found discrepancies in every system it was applied to, often differences in
the grain of atomicity.

### CCF (smart casual verification)
Howard, H., Kuppe, M. A., Ashton, E., Chamayou, A., Crooks, N. "Smart Casual
Verification of the Confidential Consortium Framework." NSDI 2025. Source:
https://arxiv.org/pdf/2406.17455
File: `howard-2025-smart-casual-verification-ccf-nsdi.pdf`. Read depth: core.

The TLA+ model is bound to the *C++* implementation and runs in CI. It found
six bugs. Depth-first trace validation took minutes where breadth-first took
about an hour.

### MongoDB (eXtreme modelling)
Davis, A. J. J., Hirschhorn, M., Schvimer, J. "eXtreme Modelling in Practice."
PVLDB 13(9), 2020. Source: https://arxiv.org/pdf/2006.00915
File: `davis-2020-extreme-modelling-in-practice-vldb.pdf`. Read depth: core.

**Model-based trace checking failed** on the MongoDB server. The project was
abandoned after 10 weeks, because:
- the abstract specification did not correspond to the implementation;
- multi-threaded state was hard to snapshot.

Making the specification less abstract grew its state space from 42K states to
371K, and checking time from 2 s to 14 min.

**Model-based test-case generation succeeded** for Realm Sync, because there
the specification was a direct transcription of the code.

The authors' advice:
- write the specification to correspond to the implementation;
- log only the variables available at the moment of each transition;
- validate modules in unit tests, not the whole system.

**Implication:** the brief's C4 (a declared `constexpr` table plus trace
validation) is in the *successful* regime, *if the implementation is driven by
the table*. Then the specification and the code cannot drift apart, and trace
validation is needed only for side effects and guards outside the table.
- A deterministic table with full traces needs no search: checking is linear in
  the trace length.
- Search is needed only for partial traces or nondeterminism.
- TLA+ export pays off only at the abstraction level where MongoDB's attempt
  failed, so it should be optional.

---

## 9. Fact stores and incremental, edit-local analysis

### QL (CodeQL)
Avgustinov, P., de Moor, O., Peyton Jones, M., Schäfer, M. "QL:
Object-oriented Queries on Relational Data." ECOOP 2016, LIPIcs 56,
doi:10.4230/LIPIcs.ECOOP.2016.2. Source:
https://drops.dagstuhl.de/storage/00lipics/lipics-vol056-ecoop2016/LIPIcs.ECOOP.2016.2/LIPIcs.ECOOP.2016.2.pdf
File: `avgustinov-2016-ql-object-oriented-queries-ecoop.pdf`. Read depth: abstract+.

Classes are logical properties, and the language compiles to Datalog on a
relational database.

### Soufflé
Jordan, H., Scholz, B., Subotić, P. "Soufflé: On Synthesis of Program
Analyzers." CAV 2016, LNCS 9780, pp. 422–430. Source:
https://static.aminer.org/pdf/20170130/pdfs/cav/i5oalygn1b0zj7m3ku9iwrc62ubpwtt8.pdf
File: `jordan-2016-souffle-synthesis-program-analyzers-cav.pdf`. Read depth: abstract+.

Soufflé compiles Datalog to C++. Points-to analysis of OpenJDK takes under a
minute.

### Doop
Bravenboer, M., Smaragdakis, Y. "Strictly Declarative Specification of
Sophisticated Points-to Analyses." OOPSLA 2009, doi:10.1145/1640089.1640108.
Source: https://inst.eecs.berkeley.edu/~cs294-260/sp24/papers/doop.pdf
File: `bravenboer-smaragdakis-2009-doop-declarative-points-to-oopsla.pdf`. Read depth: abstract+.

### Glean
Meta Engineering, "Indexing code at scale with Glean" (2024-12-19). Source:
https://engineering.fb.com/2024/12/19/developer-tools/glean-open-source-code-indexing/
(web text; not a PDF). Read depth: full (the post).

- Facts are typed predicates with per-language schemas. Language-neutral views
  are defined in the schema, like SQL views.
- Incrementality comes from *stacked immutable databases*.
- For C++, incremental indexing is at best O(fanout): a header change
  reprocesses every translation unit that includes it.
- *Diff sketches* are machine-readable summaries of a change, used to drive
  lints.
- The IDE blends Glean data with clangd's.

**Implication for the brief's fact model:**
- The brief's SQL tables over SQLite are an adequate start.
- `mutates` needs a *transitive* closure through the call graph, which is
  natural in Datalog and awkward in SQL (recursive common table expressions).
- Glean's "diff sketch" is the established name and shape for what the brief
  calls the delta.
- C++ incrementality is bounded below by header fanout. This matters for the
  daemon question.

### Laddder and IncA
Szabó, T., Erdweg, S., Bergmann, G. "Incremental Whole-Program Analysis in
Datalog with Lattices." PLDI 2021, doi:10.1145/3453483.3454026. Source:
https://www.pl.informatik.uni-mainz.de/files/2021/04/inca-whole-program.pdf
File: `szabo-2021-incremental-whole-program-datalog-lattices-pldi.pdf`. Read depth: abstract+.

Szabó, T., Bergmann, G., Erdweg, S., Voelter, M. "Incrementalizing
Lattice-Based Program Analyses in Datalog." OOPSLA 2018. Source:
https://voelter.de/data/pub/inca-oopsla2018.pdf
File: `szabo-2018-incrementalizing-lattice-analyses-datalog-oopsla.pdf`. Read depth: abstract+.

- Laddder keeps points-to, constant-propagation and interval results up to date
  within milliseconds on Java.
- It *assumes the IDE supplies incremental AST deltas*; IncA used a projectional
  editor.
- Earlier Datalog frameworks did well incrementally only for intraprocedural
  analyses.

### Adapton
Hammer, M. A., Khoo, Y. P., Hicks, M., Foster, J. S. "Adapton: Composable,
Demand-Driven Incremental Computation." PLDI 2014,
doi:10.1145/2594291.2594324. Source: https://www.cs.umd.edu/~mwh/papers/adapton-submit.pdf
(the submitted version). File: `hammer-2014-adapton-pldi.pdf`. Read depth: abstract+.

Adapton recomputes only what is *demanded*.

### Build systems à la carte
Mokhov, A., Mitchell, N., Peyton Jones, S. "Build Systems à la Carte." ICFP
2018. Source: https://www.microsoft.com/en-us/research/uploads/prod/2018/03/build-systems.pdf
File: `mokhov-2018-build-systems-a-la-carte-icfp.pdf`. Read depth: core.

Key ideas:
- definitions of *minimality* and *correctness*;
- *early cutoff*, which stops when a rebuilt result is unchanged;
- *verifying traces*, which store the hashes of a task's dependencies and
  rebuild only on mismatch;
- constructive and cloud traces;
- dynamic dependencies.

**Implication:** the brief's `preservation_dep(symbol, content_hash)` with
"conservative invalidation" is a verifying-trace rebuilder with early cutoff,
keyed on normalized-AST hashes. That design is well understood. It needs only
a persistent store, *not a resident process*.

### Three architectures for a responsive IDE
Kladov, A. (matklad), "Three Architectures for a Responsive IDE",
rust-analyzer blog, 2020-07-20. Source:
https://rust-analyzer.github.io/blog/2020/07/20/three-architectures-for-responsive-ide.html
(web text). Read depth: full (the post).

The three architectures:
1. map-reduce indexing (IntelliJ, Sorbet);
2. snapshotting the compiler after the headers (clangd's preamble, Merlin);
3. query-based laziness (salsa, rust-analyzer).

The key line: "it's not the incrementality that makes an IDE fast. Rather, it's
laziness — the ability to skip huge swaths of code altogether."

### Static analysis at Google
Sadowski, C., Aftandilian, E., Eagle, A., Miller-Cushon, L., Jaspan, C.
"Lessons from Building Static Analysis Tools at Google." CACM 61(4), 2018,
doi:10.1145/3188720. Source: https://6826.csail.mit.edu/2020/papers/google-analysis-cacm.pdf
File: `sadowski-2018-lessons-static-analysis-google-cacm.pdf`. Read depth: core.

- **Compiler-error checks** must be understandable and actionable with a
  mechanical fix. They must produce **no effective false positives**, and must
  concern correctness only.
- **Code-review checks** may have **under 10% effective false positives**. An
  "effective false positive" is any report the developer does not act on.
- Of compile-time findings, 74% were judged "real problems". Of findings in
  checked-in code, 21% were. This is the "survivor effect".
- In the 2009 FindBugs fixit, engineers reviewed 3,954 warnings and filed bug
  reports for 44% of them, yet only 16% (640) were fixed.
- New findings are distinguished from existing ones.

### Static analysis at Facebook
Distefano, D., Fähndrich, M., Logozzo, F., O'Hearn, P. W. "Scaling Static
Analyses at Facebook." CACM 62(8), 2019, doi:10.1145/3338112. Source:
https://6826.csail.mit.edu/2020/papers/facebook-infer-cacm.pdf
File: `distefano-2019-scaling-static-analyses-facebook-cacm.pdf`. Read depth: core.

The same analysis had a fix rate **near 0%** as a batch report, at under 20%
false positives. As a *diff-time* reviewer bot it rose to **over 70%**.
Compositional analysis is what makes diff-time reporting scale incrementally.

**Implication:**
- The brief's thesis that edit-local feedback beats batch is the best-supported
  claim in this whole lane.
- The brief's open question on lint thresholds has industrial answers: a
  blocking gate needs about 0 effective false positives, and advisory
  output needs under 10%.
- One gap the literature does not cover: an *agent* acts on every warning. For
  an agent, an effective false positive is not ignored. It becomes a wrong edit
  or a suppression. Agent-facing output should therefore meet the
  *compiler-check* bar, not the review bar. The decisions ledger is the
  pressure-release valve, and it must stay visible (as the brief's Goodhart rule
  already says).

---

## 10. Standard and toolchain status this lane checked

The toolchain lane owns the details. These facts bear on the literature's
recommendations:

- **The standard:** C++26 was approved at the Croydon meeting on 2026-03-28. It
  *includes* Contracts (P2900R14) and Reflection (P2996R13).
  - Sources: https://www.theregister.com/2026/03/31/cplusplus26_approved;
    P4043R0 (2026-03-07), https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2026/p4043r0
  - The vote count (114–12) comes from secondary coverage and was not checked
    against the trip report.
- **GCC:** GCC 16.1 (April 2026) implements P2996 with `-std=c++26 -freflection`
  (isocpp.org GCC 16.1 announcement; GCC status page). One secondary blog
  claims GCC 16.1 also ships contracts. **Not verified.**
- **Clang, as tested locally:** Homebrew Clang 23.1.2 rejects `pre(...)` /
  `post(...)` and `-fcontracts`, and has no `<meta>` header. Clang's own
  cxx_status page (fetched 2026-10-17) lists Reflection, Contracts and
  erroneous behaviour (P2795) as "No".
- **Side observation:** Homebrew Clang's default sysroot points at a missing
  `MacOSX26.sdk`. This is the toolchain lane's problem.

---

## Synthesis: what the brief misses or gets wrong

1. **Visible-state semantics is the wrong default, and the brief
   misattributes it.**
   - Boogie/Spec# introduced pack/unpack *because* visible-state reasoning is
     unsound under reentrancy (Barnett et al. 2004).
   - verbs needs a **callback/reentrancy transformation kind** next to unwind,
     move and escape. It must also specify *whose* invariants a visible state
     assumes (Drossopoulou et al. 2008).
   - DeLine & Fähndrich give a cleaner model: **typestates generalize
     invariants**. `visible_state`, `moved_from` and `after_point` can be
     typestates with per-state predicates, rather than an ad hoc scope enum.

2. **Single-state predicates are insufficient.**
   - Transitions, monotonicity, immutability after construction and FSM steps
     are *two-state* invariants (VCC).
   - The canonical vocabulary needs `old(·)` relations. A preservation verdict
     is itself a two-state statement.

3. **The gap query assumes stability.** Joining `mutates` to the subject misses
   multi-object (`relation`) invariants unless verbs adopts an ownership
   discipline or an explicit dependency set (Leino & Müller; Polikarpova et
   al.). Without that, the core metric of open preservation obligations
   under-counts precisely the hardest cases.

4. **Kind discovery has a known failure mode and a known fix.**
   - Static unification over arithmetic collapsed about 65% of integer queries
     into one useless class (Lackwit).
   - The fix is a deliberate *interaction definition*. Units mode unifies only
     `+`, `-` and comparisons (Guo et al.).
   - Dynamic inference was measurably more precise than Lackwit. Checking its
     result by encoding it in types makes the combination sound.

5. **The discovery loop is Houdini and Liquid inference, not new research.**
   - A fixed qualifier set (the brief's canonical vocabulary), candidate
     generation, and refutation to the maximal valid subset are an established,
     sound algorithm.
   - Daikon's null-hypothesis filter answers when to show `hypothesis` findings.
   - Houdini says to show refuted candidates and their reasons, which the
     brief's `rejected` ledger can do.

6. **LLMs have overtaken the generator side.**
   - ClassInvGen produces executable C++ class invariants that beat Daikon, with
     tests and mutants as the filter.
   - Lemur and Quokka formalize "LLM proposes, checker disposes".
   - Strategic consequence: verbs may not need to own Lackwit/Daikon-class
     inference engines. Its distinctive job is the **refuter and the record**:
     - compiler-checked encodings (vlib);
     - test and mutant filtering;
     - exhaustive throw injection;
     - the decisions ledger.
   - Blackbird is the generator. LLMs repair badly (16%), so refutations must
     carry concrete counterexamples.

7. **The parametricity framing does not transfer to C++.**
   - Templates inspect their arguments, so free theorems fail.
   - The valid claim is Reynolds' representation independence for *closed*
     vlib types.
   - The incremental cache is build-systems theory, not parametricity.

8. **The daemon is not required by the incremental design.**
   - `preservation_dep` with content hashes is a verifying-trace rebuilder with
     early cutoff (Mokhov et al.). It works from a one-shot command with an
     on-disk store.
   - Speed in IDEs comes from laziness (matklad), and clangd already provides
     it via preamble snapshots.
   - C++ incrementality is bounded by header fanout (Glean).
   - Millisecond incremental whole-program analysis exists (Laddder), but it
     needs IDE-fed AST deltas and a Datalog engine.
   - So: a resident verbs process would buy only a warm in-memory AST, which
     clangd already holds. That is evidence for the operator's review of
     whether a daemon is needed.

9. **Diff-time beats batch by an order of magnitude, and agents need a stricter
   bar.**
   - Fix rates were near 0% in batch and over 70% at diff time (Infer).
   - Google's thresholds are 0 effective false positives for blocking checks
     and under 10% for advisory ones.
   - An agent acts on every warning, so agent-facing output should meet the
     0-false-positive bar or be clearly labelled as hypothesis.

10. **Unwinding needs its dynamic oracle.** Abrahams/Arnold exhaustive throw
    injection is cheap, exhaustive over failure points, and checks the basic
    guarantee *including leaks*. The brief has only a static lint.

11. **`Bounded`'s widen-on-every-operation design cannot represent values
    carried across loop iterations.**
    - Wuffs keeps declared types fixed and proves fit with interval arithmetic
      plus explicit facts, using a deliberately fast, dumb prover.
    - verbs must choose between a checked or saturating assignment and a proof
      obligation, and say which.

12. **Trace validation works only with close correspondence to the code.**
    - MongoDB's attempt failed after 10 weeks; CCF succeeded with a model bound
      to C++ and depth-first search.
    - verbs' declared tables are in the good regime *if code is driven by the
      table*.
    - TLA+ export is optional and pays off rarely.

13. **The brief targets a stale language level.**
    - C++26 shipped Contracts and Reflection in March 2026.
      `std::meta::enumerators_of` gives an exact, complete enum domain with no
      macro and no ±128 limit, which is the stated reason for `VERBS_ENUM`.
      `pre`, `post` and `contract_assert` are a standard surface for the
      "assertion" and "construction" mechanisms.
    - Neither is in upstream Clang 23. "Clang, C++23" is defensible today for
      TSA, Consumed and LibTooling. But the decision now has a real cost and
      should be made explicitly:
      - Clang-only C++23 plus macros;
      - GCC 16 for C++26 features;
      - a design that adopts reflection when Clang gains it.

14. **For Rust (R1), Flux is the stronger realization of refined and bounded
    types** than waiting on `generic_const_exprs`. Its price is an SMT
    dependency, which the minimal-backends rule must weigh explicitly.

---

## Acquired files (SHA-256)

| File | SHA-256 |
| --- | --- |
| `akhond-2025-llm-loop-invariant-generation-fixing.pdf` | `1428e5de7f5e2116896849266873839f6601a82517837d8c2a5f58b2b8392d60` |
| `aldrich-2009-typestate-oriented-programming-onward.pdf` | `20512dcc2e165ecbcfceaefd30cea473a1b1596a4e7c911c062f20754a243a1d` |
| `ammons-bodik-larus-2002-mining-specifications-popl.pdf` | `1fd9ebc62c84181e2d827a259ff20a89fa50604e6422ab87b11d8c899fcb7b6f` |
| `avgustinov-2016-ql-object-oriented-queries-ecoop.pdf` | `ef33b7fcd5f55841a96fda0763ef71a5c482738ec0be8c0780818a36808727e8` |
| `barnett-2004-verification-oo-programs-invariants-jot.pdf` | `ac004db50bc2707578bf0d4a625976c612e1d83a0c286362e72c193449e0acc7` |
| `bravenboer-smaragdakis-2009-doop-declarative-points-to-oopsla.pdf` | `928ce283b2c9127f5f5f0ffd43108cbc4e00a4e0bee925c3a497486eb45945f7` |
| `chen-2026-beyond-basic-specifications-llm.pdf` | `826ce498b654d26a19b47e6f13d966dd9a73bd6cf88d911caa8de2ad3d7100a8` |
| `cirstea-2024-validating-traces-tla-specifications.pdf` | `229abdc0dac233c168dc086c9ae27593b8f87cadb46d65d2ee8f8750743e1965` |
| `cohen-2009-practical-verification-methodology-concurrent-programs-msr-tr.pdf` | `a0762e836aa23b3ca8ad9c25e2b1eb8f00fff3aaedd976d19c873db7d306060a` |
| `cohen-2009-vcc-practical-verifying-concurrent-c-tphols.pdf` | `2db58ca2c0cd96f4a6458fd87f233584cd2c40ba9a417379745812485b1ff75f` |
| `davis-2020-extreme-modelling-in-practice-vldb.pdf` | `aedaa6702901f1b4d2e40788247b1b3e7e995d55712561983d1399d9c4d6d8d4` |
| `deline-fahndrich-2004-typestates-for-objects-ecoop.pdf` | `7bdbb766acefe508682bbbf5a2b7de13b1f1c709997eccf9717119b0fe5c4efa` |
| `distefano-2019-scaling-static-analyses-facebook-cacm.pdf` | `3bf657de823252d6f44b96ec6b9348003b029c90abe739c707dedbf01d50a13e` |
| `drossopoulou-2008-unified-framework-object-invariants-ecoop.pdf` | `c2c6d3c87b59a10bbbe388621ce31d0e95daff37830afde2329748e4d891ef2c` |
| `endres-2024-nl2postcond-fse.pdf` | `4a95f98e49d8b511bab4c18d0c4bbf6ea95c2ab6c93b8efd5821cf1877df9ddf` |
| `ernst-2001-dynamically-discovering-likely-invariants-tse.pdf` | `0644d60bdd70a8c1efed0c9f5a300481d4ffce3900b9795801359732e804ebbc` |
| `ernst-2007-daikon-system-scp.pdf` | `f576bc8cbcb1ca30da6e7549615d0314b276e9bf924faba88ce677844031eaca` |
| `flanagan-leino-2001-houdini-esc-java.pdf` | `58852f85ca0e61502f4f95fa936206671f25df3beba932eb1a2c9ceef8177896` |
| `guo-2006-dynamic-inference-abstract-types-issta.pdf` | `be7f1727123bc6fe3b667066fe2320e32096f5f38d3d06447aa9737e1482bacf` |
| `hammer-2014-adapton-pldi.pdf` | `94a4f7354d14a67c17b6cb94813f81fb72e955f83685f6d9f19a7fb41b478cc9` |
| `hangal-lam-2002-diduce-icse.pdf` | `edbd373236154011dcf0432c2a2218469b4c2a28030e433097b86cfe9c163fb6` |
| `howard-2025-smart-casual-verification-ccf-nsdi.pdf` | `c9e5a47fb1066fe97246f6e96b39f8790d5c044e5ba756c73e7db050134be1b4` |
| `hutchins-2014-clang-thread-safety-analysis-scam.pdf` | `52363803cf635e981d6d3ad2b970cceddf1d701d12106b17a2a10b29275cfce3` |
| `jhala-vazou-2020-refinement-types-tutorial.pdf` | `38c9e9be879b6b79878b52d499504615e60c5a1f4995e64494215ec3beb6e940` |
| `jordan-2016-souffle-synthesis-program-analyzers-cav.pdf` | `bad66b1f7e5cc89c379daa6e8fb2a7f094c1ccebe18e6c490f27f01ed4b116e7` |
| `lehmann-2023-flux-liquid-types-rust-pldi.pdf` | `ab5876c1fb4aeca92dd7416172a49272009f74c7c976be51730e48968f22e403` |
| `leino-muller-2004-object-invariants-dynamic-contexts-ecoop.pdf` | `bd08b08390abebe0ce530d8bf148f1723cf3e685d397e824684b1e54169ab218` |
| `meyer-1992-applying-design-by-contract.pdf` | `bc1bab86f8753e5eafb40b7558e961b2c4bc9938c061e8dd8c141b839873ac07` |
| `mokhov-2018-build-systems-a-la-carte-icfp.pdf` | `d6c175a48cc908ca3f185e1fb4620e3278c5655218ac687d83dfa7f405624ede` |
| `nimmer-ernst-2001-static-verification-dynamically-detected-invariants.pdf` | `2483faa66513a759379a6cf8ff31affaf16057b13c65a52fca72aa415941878d` |
| `ocallahan-jackson-1997-lackwit-icse.pdf` | `6a62cce98530d6e19e96e92cdac01c340bcb7ecf46588c6064f10b848ebae4e6` |
| `pei-2023-llms-reason-about-program-invariants-icml.pdf` | `d1918926be295a8b4168a22b88e8f3d98e0b61b0f081657e975394b39b7a540a` |
| `polikarpova-2014-flexible-invariants-semantic-collaboration-fm.pdf` | `9f6eff91af433be005efc0b58379fb6bd06e55304ffb9c37cc43ac8a2c9a6578` |
| `reynolds-1983-types-abstraction-parametric-polymorphism.pdf` | `b29d6ba8e1ebc1ee8b8f41ae6aa3afcc454c3175385dcbd733e1495726c20695` |
| `rondon-2008-liquid-types-pldi.pdf` | `012964cdf4fb62b883fba9d07d87c40c84afe6871d89ec962b169725ab879ab2` |
| `sadowski-2018-lessons-static-analysis-google-cacm.pdf` | `49214856aee5f40bb8fff390d4f5643a06d03381d47fc69f1dee17d9092c21cf` |
| `sammler-2021-refinedc-pldi.pdf` | `80d43dea0e754222a6aa851c884b4d2aee59d288a0237409952e45941104c9e0` |
| `sun-2025-classinvgen-class-invariant-synthesis-llm.pdf` | `b7fce250c594c9a9ef3783339213a5bc697fd58750c47229169825c6d606a961` |
| `szabo-2018-incrementalizing-lattice-analyses-datalog-oopsla.pdf` | `a816484729fbf8662e18bd2e827d8bb01c3712a0ce73efe7786af04dcb5c0252` |
| `szabo-2021-incremental-whole-program-datalog-lattices-pldi.pdf` | `7077da9a52a7819b3e74e4e40c4d0437e2f71226f04c4855028e4995bdf7bb2a` |
| `wadler-1989-theorems-for-free.pdf` | `7437be24671baa5bc02d4c6059a2c8dbdb8dd246e147b8db3376c0725ae84d05` |
| `wei-2026-quokka-llm-invariant-synthesis-colm.pdf` | `6bf1d82883e207dafa2280c50fb99336625b64ba86d41ec1ae968052e60758cb` |
| `wen-2024-autospec-specification-synthesis-llm-cav.pdf` | `ec10b0688da0a81c80a3f2822b02e2f07a855529f9514f4da4e72640d05bdd2e` |
| `wu-2024-lemur-llm-program-verification-iclr.pdf` | `03f68bfad0cf98f1afcef71e366b201d5d0e7a405886df1fb72133cc2a667211` |

## Not acquired (shopping list)

1. Strom, R. E., Yemini, S. "Typestate: A Programming Language Concept for
   Enhancing Software Reliability." IEEE TSE 12(1):157–171, 1986,
   doi:10.1109/TSE.1986.6312929. Paywalled (IEEE); no open copy found.
2. Garcia, R., Tanter, É., Wolff, R., Aldrich, J. "Foundations of
   Typestate-Oriented Programming." ACM TOPLAS 36(4):12, 2014,
   doi:10.1145/2629609. The upapers.dcc.uchile.cl download reset the
   connection. A CMU KiltHub copy exists:
   https://kilthub.cmu.edu/articles/journal_contribution/Foundations_of_Typestate-Oriented_Programming/6605861
3. Abrahams, D. "Exception-Safety in Generic Components." Generic Programming,
   LNCS 1766, Springer 2000, pp. 69–79, doi:10.1007/3-540-39953-4_6. The text
   was read from Boost's HTML; the PDF was not acquired.
4. Cohen, E., Moskal, M., Schulte, W., Tobies, S. "Local Verification of Global
   Invariants in Concurrent Programs." CAV 2010, LNCS 6174,
   doi:10.1007/978-3-642-14295-6_42. Paywalled; the companion MSR technical
   report was acquired instead.
5. Hangal, S., Lam, M. S. "Automatic Dimension Inference and Checking for
   Object-Oriented Programs" (UniFi). ICSE 2009. The project page
   https://suif.stanford.edu/unifi/ links a PDF that was not retrieved.
6. O'Callahan, R. "Generalized Aliasing as a Basis for Program Analysis Tools"
   (Ajax). PhD thesis, CMU, 2001 (CMU-CS-01-124). Not attempted.
7. Meyer, B. *Object-Oriented Software Construction*, 2nd ed., Prentice Hall,
   1997. A book.
