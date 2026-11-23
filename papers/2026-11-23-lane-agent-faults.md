# What agents get wrong: lane report

Prepared 2026-11-23 for the verbs redesign. Question: which faults do coding
agents commit, which of them would a habit (construct plus guard) catch or
prevent, and what should seeded faults look like?

This report builds on `papers/2026-10-17-literature-agent-feedback.md` (cited
below as "feedback lane"). It does not repeat that lane's material except where
a number is needed here. Evidence strength uses that lane's scale: **S** (large
or controlled, several models), **M** (small or single-model), **W** (design
paper, vendor, preprint without controls, anecdote).

Sources read for this lane:

1. Published studies of defects in LLM-written code, from function-level
   benchmarks to agent pull requests in real repositories (sections 1–3).
2. Studies of how agents and people respond to diagnostics and suppressions
   (section 4).
3. The operator's own review record, read-only. 125 findings from 49 code
   reviews in five projects, classified by hand (section 5).
4. The seeded-fault literature already in `papers/`, re-read for what it says
   about fault realism (section 6).

No corpus tarball was extracted. Every count below comes from documents, not
from measuring code.

---

## 1. Defect taxonomies of LLM-written code (function level)

### 1.1 Tambon et al., "Bugs in Large Language Models Generated Code: An Empirical Study," EMSE 2025

arXiv:2403.08937v2, https://arxiv.org/html/2403.08937v2, accessed 2026-11-23.
PDF: `papers/tambon-2025-bugs-in-llm-generated-code-emse.pdf`.

**What it is.** The authors hand-labeled 333 buggy CoderEval samples (Python)
from CodeGen, PanGu-Coder and Codex, producing ten bug patterns (§4.1.1). They
validated the taxonomy with a survey of 34 practitioners.

**Pattern shares** (Table 2, §4.1.2). These are shares of labels; 37.8% of
samples carry more than one label.

| Pattern | Share |
| --- | --- |
| Misinterpretation | 20.77% |
| Missing corner case | 15.27% |
| Silly mistake | 9.57% |
| Hallucinated object | 9.57% |
| Incomplete generation | 9.57% |
| Wrong attribute | 8.55% |
| Non-prompted consideration | 8.15% |
| Prompt-biased code | 6.52% |
| Syntax error | 6.11% |
| Wrong input type | 5.91% |

**How it bears on habits.** In C++ and Rust, hallucinated objects, wrong
attributes, syntax errors and most wrong input types are compile errors. The
compiler is already the stop for them. Misinterpretation and incomplete
generation are task-level faults that no habit reaches. The patterns a habit
could plausibly touch are:

- *Missing corner case* (15.27%), including empty inputs, special values and
  range edges. Bounded and refined types and closed sum types turn some of these
  into compile errors or boundary rejections.
- *Wrong input type* (5.91%) in the cases a type checker would not reject.

**Precision and ergonomics.** No data on guards. The survey (§4.2.3) rated
missing corner case as the only pattern that is hard to diagnose.

**Limits.** Python, 2023-era models, single-function tasks. **M.** Read
(abstract, §4.1–4.2 via HTML).

### 1.2 Wang et al., "Towards Understanding the Characteristics of Code Generation Errors Made by Large Language Models," ICSE 2025

arXiv:2406.08731v3, https://arxiv.org/html/2406.08731v3, accessed 2026-11-23.
PDF: `papers/wang-2025-code-generation-errors-characteristics-icse.pdf`.

**What it is.** The authors coded 557 incorrect HumanEval solutions from six
models. Semantic root causes (Table II) fall into seven categories:

- condition error (missing or incorrect condition);
- constant value error;
- reference error;
- operation or calculation error;
- garbage code;
- incomplete code or missing steps;
- memory error (infinite loop).

**Findings that matter here.**

- Most errors span multiple lines, and over 40% of syntactic error locations are
  missing or incorrect code blocks (Finding 2).
- Syntactic error distributions are similar across models; semantic ones differ.

**Bearing.** This is the weakest fit to verbs of the studies here. The dominant
faults are wrong logic and missing steps, which no construct catches. **M.** Read
(§II–III via HTML).

### 1.3 Nogueira, Vieira, Campos, "Unreliable in Practice? A Comprehensive Study of Errors in LLM-Generated Code," 2026

arXiv:2608.00661v1, https://arxiv.org/html/2608.00661v1, accessed 2026-11-23.
PDF: `papers/nogueira-2026-unreliable-in-practice-llm-code-errors.pdf`.

**What it is.** 86,726 compile and runtime errors from 7 models on 1,651
competitive-programming problems in C++, Java, C and Rust. The setting is
unassisted (no IDE, no tools). Errors were labeled by GPT-4.1-mini, with exact
agreement of 0.81–0.92 against 600 hand labels (§III-B, Table IV).

**Compile errors** (Table VI, baseline prompt):

| Class | C++ | Rust |
| --- | --- | --- |
| Missing import or #include | 56.6% | 20.5% |
| Incompatible parameter types | 20.3% | 43.4% |
| Ownership and lifetime | — | 16.7% |
| Trait or type bound | — | 6.1% |

**Runtime errors** (Table X):

| Class | C++ | Rust | Note |
| --- | --- | --- | --- |
| Out of bounds | 60.0% | 28.1% | |
| Out of memory | 10.7% | 0.5% | |
| Recursion | 8.0% | 2.9% | |
| Numeric overflow | 3.8% | 44.0% | In Rust these are panics; in C++ they are silent (§IV-B) |
| Incorrect input processing | 4.3% | 22.2% | |

**Feedback repair rates** (Tables VIII, XII). With up to two feedback-driven
regenerations, "Fixed" means the program then passes all tests; "Partially
fixed" means the error is gone but tests still fail:

- missing imports: fixed 12.4%, partially fixed 68.0%;
- incompatible parameter types: fixed 7.8%, partially fixed 58.5% (the compile
  error disappears in 66.3% of cases);
- out-of-memory errors: fixed 5.0%, partially fixed 24.4%.

**How it bears on habits.**

- *Range faults lead, but differently per language.* In Rust the two biggest
  runtime classes are overflow (44.0%) and out of bounds (28.1%). In C++ out of
  bounds leads (60.0%), followed by out of memory (10.7%) and recursion (8.0%);
  overflow is only 3.8% because C++ overflow rarely crashes. Out-of-bounds
  indexing and integer overflow are what a bounded-integer and bounded-index
  habit encodes. (Corrected in check; the earlier text said the two biggest
  runtime classes were range faults in both languages.)
- *Rust shows the C++ overflows.* The 44% Rust overflow share is, in effect, a
  measurement of overflows that C++ would leave silent.
- *Compile errors are already stopped.* Rust's parameter-type and ownership
  errors are compiler stops; verbs adds nothing there except guarding the escape
  hatches agents use to make them go away (section 4).

**Limits.** Non-agentic, competitive programming, mid-size models, LLM-labeled.
Wrong-output errors are excluded. **M–S** (large n, weak labels). Read (§III–IV
via HTML).

### 1.4 Mahmud et al., "The Illusion of Safety: Multi-Tier Verification of AI vs. Human C++ Code," 2026

arXiv:2607.00107v3. Already in `papers/`. The feedback lane gave only its
abstract; the sections below were read for this lane.

**Results.**

- *Runtime violations.* AI C++ triggers ASan/UBSan at 9.3% of compiled programs
  versus 2.6% for human code. The adjusted mixed-effects OR is 2.15 (95% CI
  1.52–3.03) (§V-A, Table VI).
- *Static warnings mislead.* Under cppcheck the AI effect *reverses* once program
  length is controlled (OR 0.68, CI 0.57–0.81). Raw static-warning counts are
  "largely a code-length effect rather than a security signal" (§V-A).
- *Tests do not catch them.* 1.8% of AI programs that pass all tests still
  trigger sanitizer violations (§V-A).
- *Which violations.* Sanitizer violations in AI code are dominated by
  signed-integer overflow (CWE-190), then heap and stack buffer overflow
  (CWE-122/121). Static findings on AI code are dominated by code-quality CWEs
  (398/563/570/571) (§V-C).

**Bearing.**

- *Counting generic lint warnings measures the wrong thing.* This supports
  habits that remove a fault class by construction over habits that add generic
  warnings.
- *Seeded-fault testing needs a runtime oracle.* In C++, testing must include a
  sanitizer tier.
- *Overflow is the first C++ target.* For C++ agent code, integer overflow is the
  most frequent confirmed runtime fault.

**Limits.** Gemma 3 27B, LLaMA 3.3 70B and Qwen 2.5 Coder 32B on 851
CodeContests problems (8,918 programs): mid-size open-weight models,
competitive programming, not agents. **S** for the runtime comparison. Read (§IV,
§V-A, §V-C).

### 1.5 Mündler et al., PLDI 2025: type errors dominate compile failures

`papers/mundler-2025-type-constrained-code-generation-pldi.pdf` §1: "on average
94% of compilation errors result from failing type checks"; syntax errors are 6%
(TypeScript).

**Bearing.** When the language has types, the compiler is the main stop agents
hit. A habit that moves a discipline into the type system puts its findings into
the channel agents already handle most. **S.** Read (§1).

---

## 2. Agent-era studies in real repositories

### 2.1 Quality drift after adopting AI tools (difference-in-differences)

**He, Miller, Agarwal, Kästner, Vasilescu, "Speed at the Cost of Quality: How
Cursor AI Increases Short-Term Velocity and Long-Term Complexity," MSR 2026.**
arXiv:2511.04427v3, https://arxiv.org/html/2511.04427v3, accessed 2026-11-23.
PDF: `papers/he-2026-cursor-speed-at-cost-of-quality-msr.pdf`.

- *Design.* 806 repositories that adopted Cursor, staggered DiD (Borusyak
  estimator). SonarQube measured quality (§3.2.1).
- *Effects* (Table 2). Static-analysis warnings rise +30.26% (±6.66%) and
  cognitive complexity +41.64% (±7.62%). The paper's own text also cites 25%
  for complexity in §5; Table 2 is the estimate.
- *Not robust across estimators* (Appendix B, robustness table). TWFE agrees
  (+18.48% warnings, +26.04% complexity), but the Callaway–Sant'Anna estimator
  gives −10.49% and −3.80%, not significant. The authors attribute this to small
  cohorts and covariate handling and do not resolve it.
- *What rose* (Appendix D, Table 8, descriptive). This is a convenience sample of
  195,010 warnings, categorized by a taxonomy the first author built with
  Claude Opus 4.5. Naming conventions (+21.3 new warnings per repository per
  month), code hygiene (+16.2: commented-out code, TODOs, unused imports and
  variables), complexity (+15.3: cognitive complexity, deep nesting, nested
  ternaries, too many parameters) and style (+14.8) rose most. Bug-adjacent
  categories rose less: type safety +8.4, logic error +2.1, security +2.0,
  error handling +1.2. API usage (−4.4), concurrency (−2.0) and resource
  management (−0.4) *fell*.
- *Languages.* Mostly JS, TS and Python.

**Agarwal, He, Vasilescu, "AI IDEs or Autonomous Agents? Measuring the Impact
of Coding Agents on Software Development," 2026.** arXiv:2601.13597v2.
PDF: `papers/agarwal-2026-ai-ides-or-autonomous-agents.pdf`.

- *Effects.* Same design, with agent pull requests as the adoption event.
  SonarQube warnings rise roughly 18% and cognitive complexity roughly 39%,
  persisting after velocity gains fade (abstract, Table 2).

**Bearing.**

- *Drift is mostly not bug-shaped.* Agent adoption produces measurable
  structural drift (complexity, parameter count, hygiene) that persists, under
  two of three estimators. The categories that grew most are not bug
  categories; bug-adjacent ones grew far less.
- *Fit for nudges.* This is evidence for nudge-type habits ("too many parameters",
  "too many branches") more than for stops. It is also a warning that warning
  counts rise with code volume (compare Mahmud above).
- *Evidence strength.* **M** for the effect on warning counts (large sample,
  but the sign depends on the estimator); **W** for which rules drove it
  (descriptive appendix). Read (Table 2, Appendices B–D).

### 2.2 Chen & Jiang, "Evaluating Software Development Agents: Patch Patterns, Code Quality, and Issue Complexity," SANER 2025

arXiv:2410.12468v2, https://arxiv.org/html/2410.12468v2, accessed 2026-11-23.
PDF: `papers/chen-jiang-2025-agent-patch-patterns-code-quality.pdf`.

- *Setup.* 4,892 patches from 10 agents on SWE-bench Verified, checked with
  SonarQube before and after each patch.
- *Bugs* (§V-B). Most agents introduce no significant new SonarQube bugs.
- *Security* (§V-C). Zero vulnerabilities in any arm.
- *Divergence.* Agents change different files and functions than the gold patch
  even when tests pass.

**Bearing.** At patch scale, generic static analysis finds little in agent
patches. The faults that matter (wrong behavior that passes tests; PatchDiff
finds 29.6% of plausible patches behave differently, feedback lane §5) are
invisible to it. **M.** Read (§V via HTML).

### 2.3 Agent-written tests are weak oracles

**Banik, Chowdhury, Shamim, "All Smoke, No Alarm: Oracle Signals in
Agent-Authored Test Code," 2026.** arXiv:2606.18168v1.
PDF: `papers/banik-2026-all-smoke-no-alarm-agent-test-oracles.pdf`.

- *Setup.* 86,156 test-file patches from 33,596 agent PRs (Codex, Copilot, Devin,
  Cursor, Claude Code) in 2,807 repositories.
- *Finding.* "80.2% of test patches contain weak or no explicit oracle signals"
  (abstract).
- *Merge effect.* Strong oracles raise merge odds (OR 1.28).
- *Strength.* **M–S.** Read (abstract).

**Dipongkor, Baral, Lam, Moran, "Test Coverage Analysis of Agentic Pull
Requests," ICSME 2026.** arXiv:2607.18057v1.
PDF: `papers/dipongkor-2026-test-coverage-agentic-prs-icsme.pdf`.

- *Setup.* 4,882 AIDev agent PRs (Java and Python).
- *Coverage of changed lines.* Existing tests cover 61.5% (Java) and 27.0%
  (Python) of changed executable lines.
- *Error handling.* Try/catch constructs are the least tested: 86.0% (Java) and
  81.0% (Python) of them are missed.
- *Strength.* **M.** Read (abstract).

**Bearing.** Two of the largest classes in the operator's record are weak test
oracles and faults on error paths (section 5). These studies show the same
pattern across agents at scale.

- No construct habit fixes a weak oracle.
- A habit that makes error-path obligations explicit (section 5, class E) at
  least moves some of those faults out of the untested region.

### 2.4 Agent-introduced bugs differ from planted bugs

**Sonwane et al., "BugPilot," ICLR 2026** (`papers/sonwane-2025-bugpilot-iclr.pdf`).
Bug categories come from an LLM-aided hierarchical summarization (Appendix C).
Relevant categories:

- *C:* input validation, boundary, or sentinel handling;
- *F:* state consistency, bookkeeping or caching;
- *G:* copy semantics, aliasing or in-place mutation.

Two observations (Figure 4, §5.1):

- *Self-introduced bugs look real.* Bugs agents introduce unintentionally while
  adding features (FeatAdd) are distributed like real SWE-bench bugs.
- *Planted bugs are skewed.* Bugs agents introduce *deliberately* (BugInstruct)
  skew to state consistency and copy semantics. Rule-based SWE-smith bugs skew
  to logic and conditionals.

The figure has no per-category numbers in text. **M.** Read (§5.1, Appendix C).

**Bearing on seeded faults.** How a fault is seeded changes the distribution.
Seeds made by asking an agent to "add a bug" over-represent state faults.
Rule-based seeds over-represent conditionals. Section 6 returns to this.

### 2.5 PR-outcome studies (context only)

Three studies analyze *why agent PRs are rejected*:

- Ehsani et al., arXiv:2601.15195, `papers/ehsani-2026-where-do-ai-coding-agents-fail.pdf`;
- arXiv:2605.22534;
- arXiv:2606.13468.

Their rejection reasons are workflow-level: abandonment, duplicates, unwanted
features, CI failure. arXiv:2605.22534 finds only 35.7% of rejections reflect
clear agent failure. None classifies code faults finely enough to map to habits.
**W** for this lane. Read (abstracts only).

### 2.6 API misuse and single-statement bug templates (added in check)

**Jesse, Ahmed, Devanbu, Morgan, "Large Language Models and Simple, Stupid
Bugs," MSR 2023.** arXiv:2303.11455.
PDF: `papers/jesse-2023-llms-simple-stupid-bugs-msr.pdf`.

- *Setup.* 16,899 single-statement Java bugs (ManySStuBs4J, 16 templates such
  as CHANGE_OPERAND, SWAP_ARGUMENTS, CHANGE_IDENTIFIER, MORE_SPECIFIC_IF), with
  the prompt cut just before the buggy statement.
- *Finding.* Codex, PolyCoder and CodeGen complete with the known bug "nearly 2x
  as many" times as with the known fix; Codex avoids 13.41% of them (§IV-A,
  RQ1). In the comment-prompting experiment, SWAP_ARGUMENTS had only 4
  examples, too few to conclude anything (§IV-D).
- *Bearing.* The SStuB templates are a ready, published operator set for
  seeding single-statement faults, and LLMs do write these shapes. They are
  generic mutants, so the Just 2014 limit (section 6) applies. **M** (2021–22
  models, completion only). Read (abstract, §III–IV).

**Zhong and Wang, "Can ChatGPT Replace StackOverflow? A Study on Robustness and
Reliability of Large Language Model Code Generation."** arXiv:2308.10335,
https://arxiv.org/abs/2308.10335, accessed 2026-11-23. 1,208 StackOverflow
questions over 24 Java APIs; "even for GPT-4, 62% of the generated code contains
API misuses" (abstract). The misuse patterns are API usage rules such as
required checks and calls. **M**. Read (abstract only).

**Zhuo et al., "Identifying and Mitigating API Misuse in Large Language
Models."** arXiv:2503.22821v2, https://arxiv.org/html/2503.22821v2, accessed
2026-11-23. Python and Java; StarCoder-7B, Qwen2.5-Coder-7B, Copilot; 3,209
method-level and 3,492 parameter-level misuses annotated by hand (abstract).
Four types: intent, hallucination, missing item, redundancy. Hallucination is
the most frequent for every model (§IV-B); missing parameters are 25–29% of
Python parameter misuses (Tables II–IV). **M**. Read (abstract, §III–IV via
HTML).

**Pearce et al., "Asleep at the Keyboard?" IEEE S&P 2022.** arXiv:2108.09293,
accessed 2026-11-23. 89 CWE scenarios, 1,689 Copilot programs, "approximately
40%" vulnerable (abstract). Several scenarios are C integer-overflow and
out-of-bounds CWEs. **M**. Read (abstract only).

**Bearing.**

- In C++ and Rust, hallucinated APIs and wrong-parameter types are compile
  errors (section 1.1); the compiler already stops them.
- "Missing item" misuse (a required call or check left out) is what an
  obligation token or typestate construct encodes (section 7.5). In Rust,
  `#[must_use]` on `Result` already stops the commonest case.
- None of these studies covers C++ or Rust APIs or agents in a loop.

---

## 3. Language-specific evidence for C++ and Rust

- **C++.** The two runtime studies (1.3, 1.4) agree: out-of-bounds access and
  integer overflow dominate. Static warnings do not separate AI from human code;
  sanitizers do. I found no study of *agent* (as opposed to single-shot LLM) C++
  faults at the level of constructs. Multi-SWE-bench C++ resolve rates (0–11.6%,
  feedback lane §5) show agents are weakest there.
- **Rust.**
  - *Compile errors.* Mismatched types and ownership/lifetime errors dominate
    LLM compile errors (1.3; SafeTrans, arXiv:2505.10708, reports E0277/E0308
    as most frequent, search-level).
  - *Escape hatches under pressure.* Under borrow-checker pressure, LLMs
    "frequently resort to unsafe blocks or raw pointers to suppress compiler
    errors" (AdaTrans, feedback lane §2).
  - *Clippy counts.* Clippy alert counts are the standard idiomaticity metric in
    C-to-Rust work (SACTOR, arXiv:2503.12511). Two studies caution that Clippy
    alone does not measure idiomaticity (arXiv:2511.20617, arXiv:2602.00840).
    All search-level.
- **Gap.** I found no study measuring precision of Clippy or clang-tidy findings
  *on agent-written code*, nor one counting how agents dispose of them. The
  operator's record (section 4.4) is the only source I found for that. The
  checker found one Java/SonarQube study of an agent triaging warnings into fix
  or suppress (CodeCureAgent, 4.3a), and none for C++ or Rust.

---

## 4. How agents and people respond to diagnostics and suppressions

The feedback lane covers the in-loop evidence: SWE-agent edit gate, generative
compilation, Dolcetti, AutoVerus, ImpossibleBench, AdaTrans and the Kiro usage
data. Only what bears on habit guards is added here.

### 4.1 Feedback helps most on mechanically named faults

- **Zhang & Kothari (2026).** Syntactic and runtime errors are far more tractable
  under iterative feedback than logic errors (feedback lane §1).
- **Nogueira (1.3).** With two retries on raw compiler feedback, the
  parameter-type error itself disappears in 66.3% of cases, but the program
  passes its tests in only 7.8%. The diagnostic gets the finding cleared; it
  does not get the program right. For verbs this means a cleared stop is not
  evidence that the underlying fault is gone. (Corrected in check; the earlier
  text read 7.8% as the rate at which the diagnostic was acted on.)
- **AutoVerus (feedback lane §2).** One typed error plus repair guidance specific
  to its class works.

Together these say a habit's finding should name the construct to use.
"Use `Bounded<0, N>` here" beats "possible overflow".

### 4.2 Pressure produces bypasses

- **ImpossibleBench.** Feedback loops raise cheating from 33% to 38% while
  raising legitimate passes from 80% to 83% (feedback lane §4).
- **AdaTrans.** LLMs use `unsafe` to silence the borrow checker.
- **Blackbird, raw partition claim (C++).** Here the agent's suppressions
  carried reasons, and the reasons were not enough:
  - *The episode.* The review recorded "R2: new lint suppressions violate the
    working requirement. The new moved-from and invalid-enum cases introduced
    NOLINT annotations"
    (`~/projects/blackbird/papers/2026-10-11-raw-partition-claim-code-review.md:28-34`).
    The journal says these suppressions "state their exact purpose"
    (`~/projects/blackbird/JOURNAL.md:6595`).
  - *Resolution.* Root rejected them anyway, and the owner removed all of them by
    constructing the inputs differently (`JOURNAL.md:6621-6624`).
  - *Lesson.* A recorded reason is not proof that a bypass was necessary.

### 4.3 People suppress too, and half their suppressions go stale

**Hu, Wang, Rubin, Pradel, "An Empirical Study of Suppressed Static Analysis
Warnings," FSE 2025** (DOI 10.1145/3715729). PDF:
`papers/hu-2025-suppressed-static-analysis-warnings-fse.pdf`, from
https://people.ece.ubc.ca/mjulia/publications/Suppressed_Static_Analysis_Warnings_FSE2025.pdf,
accessed 2026-11-23.

- *Setup* (§2.2). 46 open-source Python projects using Pylint (RQ1), of which
  10 were studied in depth (RQ2–RQ4; 1,873 suppressions at the newest commit).
  Checkstyle, PMD and ESLint appear only in 46 student Java/JavaScript projects
  (RQ1, RQ5).
- *Findings* (abstract, §1):
  - 7,357 suppressions in 46 Python projects;
  - suppression counts rise continuously over time;
  - **50.8% of suppressions affect no warning**, measured on the 10 Pylint
    projects (not across all four analyzers);
  - some, including useless ones, hide warnings introduced later;
  - developers suppress because of false positives, poor configuration and
    misleading messages.

**Bearing on "way past with a reason".**

- *Staleness is the normal state of a suppression,* not a rare case. A way-past
  that does not report "this reason no longer suppresses anything" will rot.
- *Rust already reports it, per tool.* `#[expect(lint, reason = "...")]`
  (stable since Rust 1.81, https://blog.rust-lang.org/2024/09/05/Rust-1.81.0/,
  accessed 2026-11-23) reports `unfulfilled_lint_expectations`. Checked in this
  check with rustc 1.99.0 and clippy 0.1.99: plain `rustc` reports a stale
  `#[expect(unused_variables)]` but stays silent on a stale
  `#[expect(clippy::needless_return)]`; only `clippy-driver` reports the
  latter. A staleness gate must run the tool that owns the lint.
- *C++ has no equivalent (verified).* In clang-tidy 23.1.2 the NOLINT handler
  diagnoses only unmatched `NOLINTBEGIN`/`NOLINTEND`
  (`quarantine/llvm-project/clang-tools-extra/clang-tidy/NoLintDirectiveHandler.cpp:181-193`,
  LLVM 23.1.2 per `cmake/Modules/LLVMVersion.cmake`), and the pinned
  binary's `--help` lists no unused-suppression option. A reason is optional free
  text after `NOLINT:` (`clang-tools-extra/docs/clang-tidy/index.rst:541`).
  `[[clang::suppress]]` covers only the static analyzer and has no unused report
  either (`clang/include/clang/Basic/Attr.td:3496`, `AttrDocs.td:6632`). The C++
  backend must own this.
- *Other ecosystems ship it.* ESLint's `reportUnusedDisableDirectives` defaults
  to `"warn"` and takes a reason after `--`
  (https://eslint.org/docs/latest/use/configure/rules); mypy has
  `warn_unused_ignores` (default off,
  https://mypy.readthedocs.io/en/stable/config_file.html); Pylint has
  `useless-suppression`, off by default (Hu §6). Both pages accessed 2026-11-23.

**M** (large sample, but the staleness figure is one analyzer, one language).
Read (abstract, §1–2, §6).

### 4.3a An agent given a suppress path uses it for a third of warnings (added in check)

**Joos, Bouzenia, Pradel, "CodeCureAgent: Automatic Classification and Repair
of Static Analysis Warnings," FSE 2026** (DOI 10.1145/3808140). arXiv:2509.11787v1,
https://arxiv.org/html/2509.11787v1, accessed 2026-11-23.

- *Setup.* 1,000 SonarQube warnings (291 rules) from 106 Java projects. A
  classifier sub-agent labels each warning true or false positive; true
  positives go to a repair sub-agent, false positives are suppressed, preferring
  a line-level `//NOSONAR` over a scoped `@SuppressWarnings` (§3.4).
- *Findings.* The agent labeled 30.4% of warnings false positive and suppressed
  them (§1, Table 3). On 291 hand-checked cases, classification was 91.8%
  correct: 97.4% on true positives, 81.0% on false positives (§4.2). Plausible
  fixes for 96.8%; 86.3% correct on manual inspection.
- *Bearing.* This is a designed suppress path, not an agent improvising one, and
  the tool requires no written reason. It shows that an agent offered a cheap
  way past will route a large share of findings through it. A verbs way past
  should cost a reason and be reported per change (Open question 3).

**M** (Java, one analyzer, designed pipeline). Read (abstract, §1, §3.4, §4.2
via HTML).

### 4.4 Agents comply when the fix is a type

This evidence comes from the operator's record, not the literature.

**Blackbird's gate.** Its `.clang-tidy` enables five checks plus
`clang-analyzer-*` with `WarningsAsErrors: '*'`
(`~/projects/blackbird/.clang-tidy`, commit `afacae8`):

- `bugprone-use-after-move`;
- `bugprone-unchecked-optional-access`;
- `bugprone-easily-swappable-parameters`;
- `performance-unnecessary-copy-initialization`;
- `performance-unnecessary-value-param`.

**What the journal shows.**

- *Swappable parameters.* `bugprone-easily-swappable-parameters` stopped
  agent-written code at least 10 times (`JOURNAL.md` lines 1073, 1344, 2238,
  6616, 9294, 9946, 10519, 11578, 12511, 12596; line 7188 records an 11th,
  "convertible placeholder outcome/count parameters", fixed with a native `u8`
  enum). No recorded fix suppressed. The fixes (corrected in check; the earlier
  text said every fix introduced a named type):
  - named types or aggregates in 7: `TerminalScrollUpdate` (2238), one `Queue`
    value (9294), typed cell widths and `Rect` (10519),
    `TerminalProcessJoin{queued, next}` with designated initializers (11578),
    `SchemaValue` / `ReplyCommand` (12511), a `RuntimePath` aggregate (12596),
    the `u8` enum (7188);
  - compile-time field offsets or widths in place of runtime integers in 2
    (1344, 6616);
  - a narrowed `Deadline` constructor (1073) and a helper cut to one parameter,
    `read_control(int)` (9946, a root-authored test helper).
  Several of these sites are test helpers, not production code.
- *Unchecked optionals.* `bugprone-unchecked-optional-access` stopped agent code
  at least 5 times (lines 1520, 6066, 7189, 8942, 12511). It was fixed by
  explicit presence checks ("without suppressions", line 7189).
- *Two suppressions survive, both in tests.* `tests/foundation_test.cpp:138,140`
  carry `NOLINTNEXTLINE(bugprone-use-after-move,clang-analyzer-cplusplus.Move)`
  with a comment "Deliberately test the documented rejection by a moved-from
  registry" (added in `017e671`, 2026-10-06; `JOURNAL.md:1075-1076`: "two exact
  test lines have documented analyzer suppressions"). The R2 suppressions were
  added later for the same kind of moved-from and invalid-enum test inputs and
  were reverted; R2 says "Existing historical annotations are not permission for
  new ones." (Corrected in check; the earlier text said no suppressions
  survived.) The pattern matters for verbs: negative tests that exercise a
  construct's forbidden use are where a way past is genuinely needed.

**Bearing.**

- *Agents fix stops that point at a type.* When a stop has a mechanical,
  type-introducing fix, agents in this workflow take it. This is a stop with a
  built-in construct: the field realization of a habit.
- *Confounds.* The workflow also has a hard rule against new suppressions
  (`JOURNAL.md:5809`) and an independent review that enforces it. Nothing
  separates "agents prefer the type" from "agents were forbidden to suppress".

**W–M** (one operator, one project, uncounted denominator: how often the check
fired without a journal note is unknown).

---

## 5. The operator's record: 125 classified findings

### 5.1 What was counted

**Population.** Written code reviews of agent-written code in the operator's
projects. The work in these projects is done by agents under the doctrine's
root/owner/subagent workflow (`~/projects/BLACKBIRD.md:88-90`); reviewers are
other agents or "root". Reviews of designs and plans were excluded. Read-only;
nothing was written outside verbs.

**Sample.** 49 review files (all paths under `~/projects/`):

| Project | Language | Files | How chosen | Findings |
| --- | --- | --- | --- | --- |
| blackbird (`afacae8`) | C++ | 14 | all first-round `*code*review*.md` (rereviews skipped) | 45 |
| BRepGPU (`f80ff37`) | C++/CUDA (+Python oracles) | 13 | 12 drawn at random, seed 20261123, from 59; plus one read first | 10 |
| oxcart native (`8941e1e`) | Objective-C++ | 10 | the 10 non-Rust files among 12 drawn at random, seed 20261123, from 49 | 29 |
| oxcart controller/table | Rust | 5 | all Rust code reviews | 9 |
| salib (`5bca264`) | Rust | 2 | the correctness review and the Kani bug-fix journal | 10 |
| deleuze (`f8dd911`) | Rust (+Python/Node clients, installer) | 5 | all `papers/reviews/*code*` files | 22 |
| **Total** | | **49** | | **125** |

**Selection caveat (added in check).** Two populations do not reproduce from
the stated rules. At `8941e1e`, oxcart `papers/` holds 56 files matching
`*code*review*` or `*review*code*`, not 49. At `f8dd911`, deleuze
`papers/reviews/` holds 9 `*code*` files, 6 of which enumerate findings
(read-gate binary, clients, gates, json, native, shutdown: 37 enumerated items
before excluding deferred or non-defect items), not 5 files. The class counts
below are the lane's; the checker confirmed the arithmetic and spot-checked 12
findings against their sources, not the selection.

**Language split.** 84 findings from the C++ family, 41 from Rust. Of the 22
deleuze findings, about 5 concern the non-Rust clients or installer.

**What a finding is.** A defect a reviewer stated and the owner corrected,
including defects in tests and fixtures. Excluded: items the review itself
called non-defects (for example accepted TOCTOU limits) and "checked and sound"
notes.

**Who classified.** One classifier (this lane), with no second rater. Classes
are exclusive: each finding got its single best class.

### 5.2 Classes and counts

| Class | n | What it looks like in the record | Habit |
| --- | --- | --- | --- |
| **T** Test oracle too weak | 22 | Negatives all fail on CRC so semantic checks go untested; swapped request/return refs pass; fixture passes by reading data written before the fault; guard never exercised | none (see 7.6) |
| **L** Domain or algorithm logic | 18 | LARS tie handling; self-deadlock on held capacity; quarantine of every clean restart; spec tie-breaking | none |
| **S** Lifecycle/state | 15 | Late acknowledgement overwrites Stop; journal failure overwritten to "completed"; `poisoned` downgraded to `blocked`; queued Close runs after failure and marks the run clean; known fence not retained, so admission succeeds after fencing | **state machine** (existing) |
| **E** Effect ordering and error paths | 13 | Success emitted before the return value is built, then a second terminal; an attempt left without a terminal on a cancel path; a by-value move allocates after the commit point; errno read after intervening calls; errno dropped across RPC | candidate: **obligation token / commit point** (partial) |
| **I** Identity and provenance | 12 | Status recomputes "latest task" at publication and reports task B for A's request; late receipt stamped with the *current* activity; key uses a changing window id; approval reused by version, not content; resident count used where total count was meant; content-view vs superview coordinates | **strong identifiers** (partly ships today) + candidate: **captured origin** |
| **N** Numeric range and representation | 12 | i64 range size overflow; NaN/∞ returned as `Ok`; output overflow silently becomes zero; parser advertises a cap the consumer refuses; 300 KiB events vs a 256 KiB reader ceiling; −0.0 sign lost | **bounded types** (existing) + float refinement |
| **H** Harness, build, UI, perf | 11 | Mutation guard omits CMakeLists.txt; atomic counter in a serial path; UI field shrank | none |
| **D** Docs and claims drift | 9 | README describes removed behavior; shutdown guarantee overstated; captions omit preparation | none |
| **P** Lax parsing / sentinel conflation | 7 | `as_str()` collapses `phase: true` to absent; serde derive accepts a positional array despite `deny_unknown_fields`; one enum arm (`Ambiguous`) left unconstrained; empty summary list vacuously accepted; empty profile treated as present; site 0 accepted | **ADT / closed sum type** (existing) |
| **R** Resource ownership and lifetime | 5 | Rust `Child` dropped without kill, orphaning children; test failure leaves stopped processes; borrowed lane declared after its user (destruction-order UAF); inherited pipe write end | candidate: **owned resource** |
| **G** Gaming / suppression | 1 | New NOLINTs (R2 above) | **way past with a reason** (cross-cutting) |

**Per project.**

- *blackbird (45):* T13, E7, L7, R4, S3, P3, H3, I2, N2, G1.
- *BRepGPU (10):* H3, D3, T2, N1, L1.
- *oxcart native (29):* S11, I8, L4, E2, T2, H1, D1.
- *oxcart Rust (9):* P4, I2, R1, L1, S1.
- *salib (10):* N7, D2, L1.
- *deleuze (22):* T5, L4, E4, H4, D3, N2.

**Reading the counts.**

1. **About half the findings are beyond any habit.** T + L + H + D = 60 of 125
   (48%). No construct prevents a weak test, a wrong algorithm or an overstated
   claim.
2. **The three starter habits cover S + P + N = 34 findings (27%) at most.**
   Read closely, a construct would *reject* (not merely make visible) about:
   - 8 of the 15 S findings: absorbing terminal states, "no transition out of
     Failed except recovery", and generation-checked late completions;
   - 6 of the 7 P findings: closed parse into a sum type, `Option` in place of
     `""`, `NonZero`, per-variant fields;
   - 8 of the 12 N findings: integer ranges and finite floats. The −0.0,
     subnormal-monotonicity and tie cases are not range faults.

   That is about 22 findings (18%).
3. **Candidate new habits cover I + R + E + G = 31 findings (25%) at most.**
   Conservatively about 15:
   - most swaps and identity conflations, via strong IDs and captured origin;
   - the 3 process-ownership findings, via an owned child type that kills and
     reaps;
   - about 5 of 13 E findings, via a must-consume terminal token and an error
     type that carries native detail.
4. **Language split.**
   - *C++/Objective-C++:* S and I dominate, especially in callback-driven native
     UI code (oxcart: 19 of 29).
   - *Rust:* N dominates in numeric code (salib); P dominates in protocol code
     (oxcart controller). Serde-derive leniency and `as_str()` collapse are
     Rust-specific traps.
5. **Severity.**
   - *Rust high findings.* Severity scales differ by project (oxcart:
     High/Medium; deleuze: Critical/Important/Minor; blackbird and oxcart
     native: P1/P2 or Low/medium). Of the four oxcart "High" Rust findings,
     three are construct-addressable classes: E-02 (I), E-03 (S) and CT-01 (R).
     The fourth, E-01, is L. Deleuze's only Critical, J1 (B2 tie-breaking
     diverges from JS, Python and serde_json,
     `deleuze/papers/reviews/read-gate-code-json.md:45`), is also L.
     (Corrected in check; the earlier text omitted J1.)
   - *Objective-C++ P1.* The single P1 in `native-apparatus` is an I.
   - *Tests and docs.* T and D findings were mostly Low or Medium.

### 5.3 Representative findings by class (exact sources)

- **S:**
  - `oxcart/papers/2026-10-30-native-apparatus-code-review.md:16-35`: delayed
    acknowledgement overwrites Stop; journal failure overwritten.
  - `oxcart/papers/table-evidence-code-review.md` E-03: a failed closing write
    marks the run clean.
  - `blackbird/papers/2026-10-02-u1-physical-replay-code-kimi-review.md` D1:
    `poisoned` downgraded to `blocked`. The reviewer's fix is one line:
    `if (state_ != poisoned) state_ = blocked;`.
- **I:**
  - `oxcart/papers/controller-agent-proposals-code-review.md` CA-03: status
    carries no task identity, so A's request returns B.
  - `native-apparatus` finding 4: late receipt stamped with the current activity.
  - `table-evidence` E-02: approval reused by version while content changed.
  - `blackbird/papers/2026-10-11-command-live-raw-code-review.md` finding 2:
    "Swapped references/native control fields can pass these tests".
- **P:**
  - `controller-agent-proposals` CA-01 (`as_str()` collapse), CA-02 (vacuous
    empty summary), CA-04 (serde sequence form).
  - `controller-table-service-code-review.md` CT-02: unconstrained `Ambiguous`
    variant.
  - `blackbird/JOURNAL.md:73-79`: empty `task_id` looked up as an existing task.
- **N:**
  - `salib/papers/2026-10-07-correctness-review.md` (four findings);
  - `salib/journal/2026-10-06-kani-bug-fixes.md` (i64 range-size overflow, fixed
    with i128);
  - `blackbird/papers/2026-10-11-raw-instrumentation-code-review.md` (ordinal
    exhaustion; 300 KiB vs 256 KiB).
- **E:**
  - `command-live` finding 1: success before construction, double terminal.
  - `blackbird/papers/2026-10-11-task-owner-raw-code-review.md` §1: a by-value
    `Prepared` move allocates after the accepted append (libstdc++13 deque move
    constructor).
  - `oxcart/papers/native-control-helper-code-review.md` NC-3: errno read after
    Foundation calls.
- **R:**
  - `controller-table-service` CT-01. "Dropping a Child does not terminate or
    reap it", per Rust 1.94.1 `std::process` docs, as cited by the reviewer.
  - `blackbird/papers/2026-10-11-authored-raw-code-review.md`: lane declared
    after `CodingEngine`, giving EXC_BAD_ACCESS on destruction.
- **T:**
  - `blackbird/papers/2026-10-01-u1-head-kimi-code-review.md` F1: every negative
    invalidates the CRC.
  - `blackbird/papers/2026-10-11-resource-sampler-code-review.md` finding 1:
    passes by reading pre-death data.

### 5.4 Agent-behavior signals in the record

- **The journal repeatedly asserts that nothing was weakened.** The word
  "weaken" appears on 18 lines of `JOURNAL.md` (`grep -ci weaken`), nearly all
  disclaimers such as "without weakening" or "no … weakening". The workflow treats weakening tests, deadlines and
  rules as a known agent failure that must be disclaimed each time.
- **One fabricated-field fault.** "A fabricated allocation Error … the accepted
  plan emits Error fields only when owned" (`JOURNAL.md:7574-7578`). This is a P
  fault: fields attached to a variant that must not carry them.
- **Test oracles were set as upper bounds.** One entry records oracles written as
  upper bounds instead of exact values (`JOURNAL.md:11975-11977`). Compare
  Banik's 80.2% weak oracles (2.3).

### 5.5 What this sample cannot say

- **No rates.** There is no denominator of lines or edits, so these are class
  shares among reviewer-found defects, not fault rates.
- **Caught faults only.** The reviews found these faults; faults that escaped
  review are absent by construction.
- **Biased source.** The operator's projects are protocol-, durability- and
  callback-heavy. That inflates S, I and E relative to, say, numeric kernels.
  salib shows the opposite skew.
- **One rater.** Classes overlap. For example, CA-03 is I or S, and the
  command-live swapped refs are T or I. A second rater would move several
  counts.

---

## 6. What seeded faults should look like

The verbs requirement is that seeded faults test the *guards* on real corpora.
Two literature results constrain the seeding:

- **Generic mutants are a partial proxy.** 27% of real faults are coupled to no
  standard mutant (Just 2014, feedback lane §5). Mull's IR operators seed
  generic faults, not habit-shaped ones. The SStuB templates (2.6) are the one
  generic set with evidence that LLMs write those exact shapes.
- **The seeding method shapes the distribution** (BugPilot, 2.4). Asking an
  agent to plant bugs over-represents state and aliasing bugs. Rule-based edits
  over-represent conditionals. Faults agents introduce while doing real feature
  work look most like real bugs.

**Per-class seeds, taken from the record (5.2).** Each seed is a source edit
that compiles. The guard must fire at the stated place, and the seed passes only
if it does. These are the fault shapes; the operators themselves are design
work.

| Class | Seed (C++) | Seed (Rust) | Origin in record |
| --- | --- | --- | --- |
| S | Assign the state field directly, outside the transition function. Remove the terminal-state check in a completion callback. Let a stale-generation completion through | `self.state = …` outside the transition `impl`. Drop the generation compare in a late-reply handler. Add a `Failed → Closed` arm | apparatus 1–2, E-03, D1 |
| I | Swap two adjacent same-typed arguments. Replace a captured origin id with the ambient "current" one. Compare by version instead of content | Same, with newtype ids unwrapped to `u64`. Read `self.current_task` in a reply path | CA-03, E-02, apparatus 4, command-live 2 |
| P | Replace `std::optional<T>` with `T` plus `""`/`0` sentinel. Add `default:` to a switch over an owned enum. Accept a zero id | `.as_str().unwrap_or("")`. `_ =>` arm on an owned enum. Typed deserialize without a shape precheck. `iter().all()` acceptance over a possibly-empty list | CA-01/02/04, CT-02, site0 |
| N | Widen a bounded integer to raw `int64_t`. Remove a range check before indexing. Unchecked `a - b` on a width | `as` truncating cast. `wrapping_*` or unchecked arithmetic. `f64` result returned without a finiteness check | salib, raw-instrumentation |
| R | Drop the kill/reap in a child owner's destructor. Reorder member or local declarations so a borrower outlives its owner. Open an fd without CLOEXEC | Hold `std::process::Child` without a kill-on-drop owner. Spawn a thread holding a child without a join | CT-01, authored-raw, raw-instrumentation |
| E | Emit success before the fallible construction step. Take a by-value parameter at a commit point. Read `errno` after an intervening call | Return early before consuming a terminal token. Map an `io::Error` to a unit error variant | command-live 1, task-owner 1, NC-3, raw-admission 1 |
| G | Add `// NOLINT` (with and without reason). Add a `.clang-tidy` override. Weaken a habit type to its raw representation | `#[allow(...)]` without reason. `#[expect]` whose lint no longer fires. `unsafe` added near a borrow error | R2, AdaTrans |

**Oracle tier.** For N and R in C++, a seeded fault the guard misses should also
be checked under ASan/UBSan. Mahmud (1.4) shows static silence is not runtime
safety. This gives a second oracle that says whether the miss matters.

**Natural faults.** BugPilot-style feature tasks on the corpus produce
agent-introduced faults whose classes are unknown in advance. These are the
realistic test of whether guards fire on the faults agents *actually* write, as
opposed to the faults we expect.

---

## 7. Mechanisms, one by one

Each subsection below covers what a mechanism is, which habit part it carries,
the evidence on precision and ergonomics, and its costs. These are the
mechanisms this lane's evidence points at, not designs.

### 7.1 Typed state machine (existing starter habit) → class S

- **Construct.**
  - *C++:* states as a `std::variant` of per-state structs; transitions as
    functions taking the old state by `&&` and returning the new one; terminal
    states with no outgoing transition.
  - *Rust:* an `enum` with by-value `match self` transitions, or typestate
    generics where a static protocol allows.
  - *Late completions:* these carry a generation or origin token, and the
    transition function rejects a mismatch.
- **Stops.** A write to the state field outside the transition function
  (bypass). A transition out of a terminal state (misuse; a compile error when
  terminal is a distinct type).
- **Nudges.** Several `bool` members written together, or an `enum` plus `bool`s
  that are always set in the same statements (the operator's "three bools" case;
  clippy `struct_excessive_bools` is the exact-rule analogue). A string field
  compared against two or more literals.
- **Evidence.**
  - *Record:* 15 of 125 findings, the largest class a construct can address.
    About 8 would be rejected by absorbing terminals plus generation checks.
    Concentrated in async and callback code: 11 in oxcart native.
  - *Literature:* BugPilot's state-consistency category (2.4) is the nearest
    match. **No precision data exists** for either nudge.
  - *Prior verbs nudge:* the enum-candidate heuristic reached 46–62% held-out
    precision (`papers/2026-10-17-enum-candidate-redesign.md`, Verdict). The
    string-against-literals nudge inherits that difficulty.
- **Costs.**
  - *C++:* variants and visitors produce poor diagnostics. Terminal-state-as-type
    needs the owning object to change type, which fights long-lived owners. The
    record's owners (`JournalWriter`, `Store`) are long-lived.
  - *Rust:* a by-value transition on a field needs `mem::replace` or `Option`
    take.

### 7.2 Strong identifiers and captured origin (partly shipping; candidate) → class I

- **Construct.** Distinct types for distinct ids and quantities (task id,
  activity id, request ref, "resident count" vs "total count", coordinate
  frame). "Captured origin" means a callback or reply type that must be built
  from the identity captured at dispatch; it has no constructor from ambient
  state.
- **Stops.**
  - `bugprone-easily-swappable-parameters` already ships in clang-tidy and is
    already on in blackbird.
  - Rust: no Clippy equivalent (verified in check against the full lint list
    of clippy 0.1.99, `clippy-driver -W help`). The nearest are
    `too_many_arguments`, `fn_params_excessive_bools` (pedantic) and
    `similar_names` (pedantic), none of which looks at adjacent same-typed
    parameters. A Rust stop would be owned machinery.
  - Bypass: unwrapping an id to its raw integer in a comparison or a map key.
- **Nudge.** A reply or completion handler reading a "current" or "latest" member
  instead of a captured one.
- **Evidence.**
  - *Ergonomics (section 4.4):* the strongest positive evidence in this lane. At
    least 10 swappable-parameter stops in blackbird were each fixed by a named
    type, none suppressed.
  - *Precision (added in check).* The clang-tidy check flags function
    *definitions* whose adjacent parameters could be mixed; it is an exact
    interface rule, not a bug detector, so bug-finding precision is not its
    metric. Its design paper (Szalay, Sinkovics, Porkoláb, SCAM 2020,
    `papers/szalay-2020-implicit-conversions-argument-swapping-scam.pdf`) reports
    report counts on open-source C and C++ projects: modelling implicit
    conversions raises them "markedly", and the relatedness heuristics cut
    them by 40% on average (§V). Length-2 ranges are over half of all reports.
    The call-site form, which compares argument names with parameter names, has
    measured precision. Rice et al., "Detecting Argument Selection Defects,"
    OOPSLA 2017 (`papers/rice-2017-detecting-argument-selection-defects-oopsla.pdf`):
    on 200 million lines at Google, an 85% true-positive rate at the high
    threshold (459 true, 78 false), and 2,060 true and 1,207 false at the low
    one (abstract). It ships in Error Prone (Java). A Rust nudge could follow it.
  - *Record:* 12 findings, including one High in Rust (E-02) and the single P1
    in Objective-C++.
- **Costs.**
  - *Strong-typedef libraries:* NamedType, strong_type and type_safe are in
    `quarantine/`; mp-units for quantities. They raise template diagnostics and
    compile time; the cpp-toolchain-burdens lane covers this.
  - *Captured origin:* this has no off-the-shelf check; it is owned machinery.

### 7.3 Closed sum types and strict parsing (existing ADT habit) → class P

- **Construct.**
  - *C++:* `std::optional` and `std::variant` instead of sentinels; owned enums
    with no default; strong `NonZero<T>`.
  - *Rust:* enums with per-variant data, and a parse layer that admits only the
    closed shape. CA-04 shows `deny_unknown_fields` is not enough: derived serde
    also accepts the sequence form.
- **Stops.**
  - `-Wswitch-enum` / `clippy::wildcard_enum_match_arm` on owned enums (bypass
    of exhaustiveness).
  - `""`, `0` or `-1` compared as an absence marker on a field of habit type.
  - In Rust, `unwrap_or_default` / `unwrap_or("")` on a parse result of a habit
    type.
- **Nudge.** An acceptance predicate computed by `all` or `none` over a
  collection with no emptiness check (CA-02).
- **Evidence.**
  - *Record:* 7 findings; about 6 would be rejected.
  - *Literature:* Tambon's missing corner case (15.27%) and BugPilot's sentinel
    category are the nearest published classes. No precision data for these
    guards on agent code.
- **Costs.** Few. The construct is native in Rust; in C++, `std::variant`
  ergonomics are the cost.

### 7.4 Bounded and refined numbers (existing starter habit) → class N

- **Construct.**
  - Range-carrying integers (`bounded-integer` and `safe_numerics` in
    `quarantine/`) and index types tied to a container's extent.
  - A finite-float type that cannot hold NaN or ∞.
  - Limits shared between components as one type, so "parser cap" and "consumer
    cap" cannot disagree (BRepGPU CLI; 300 KiB vs 256 KiB).
- **Stops.**
  - Narrowing or `as` casts out of a bounded type (`-Wconversion`,
    `clippy::cast_possible_truncation`).
  - Raw arithmetic on bounded values (`clippy::arithmetic_side_effects`).
  - Constructing a finite float from an unchecked expression.
- **Nudges.** Raw integer parameters named like counts or indices.
- **Evidence.**
  - *Literature:* the strongest of any class for C++. Overflow and out-of-bounds
    dominate confirmed runtime faults in LLM C++ (1.3: 60% OOB of C++ runtime
    errors; 1.4: CWE-190 most frequent sanitizer violation).
  - *Record:* 12 findings, concentrated in Rust numeric code. About 8 would be
    rejected at a boundary. The type makes the failure loud; it does not make
    the arithmetic right.
  - *Precision:* none on agent code. Clippy's arithmetic and cast lints are
    restriction or pedantic precisely because they fire everywhere.
- **Costs.** Generic code noise and compile time in C++ (template-heavy
  libraries). Rust needs a newtype plus operator impls per range.

### 7.5 Obligation tokens and owned resources (candidate) → classes E and R

- **Obligation token.** A terminal-or-receipt token created when an attempt
  opens and consumed exactly once.
  - *Rust:* a `#[must_use]` type whose `Drop` panics in debug (a drop bomb).
  - *C++:* a `[[nodiscard]]` move-only type with a destructor assertion;
    `bugprone-use-after-move` catches double consumption.
  - *Error types:* errors carry native detail (errno) from the point of capture.
- **Existing partial stop (added in check).** `clippy::zombie_processes`
  (suspicious group, warn by default) fires when a spawned `Child` is never
  `wait()`ed. Per `cargo clippy --explain zombie_processes`, the `wait()` must be
  unconditionally reachable after the spawn in the same body. CT-01's child was
  held by an actor beyond the spawning function and orphaned on a terminal
  fault, which is outside that documented scope.
- **Owned resource.** Rust: a `Child` wrapper that kills and reaps on drop.
  C++: RAII process and fd owners, CLOEXEC by default, and lifetime annotations
  (`[[clang::lifetimebound]]`) on borrowers.
- **Stops.**
  - Holding a raw `std::process::Child` or raw fd outside the owner (bypass).
  - A function that opens an attempt and has a path that returns without
    consuming its token.
- **Evidence.**
  - *Record:* E 13 and R 5. About 5 E and 3 R would be rejected.
  - *Literature:* error-handling code is the least tested part of agent PRs (2.3:
    86% and 81% missed), so faults there survive tests. No guard precision data.
- **Costs.**
  - *C++:* no linear types, so "consumed exactly once" is a runtime assertion
    plus a partial static check.
  - *"No fallible operation after the commit point"* (task-owner 1) is not
    expressible as a type in either language. It is a review-level property.

### 7.6 Way past with a reason (cross-cutting) → class G, and every habit

- **Mechanism.**
  - *Rust:* `#[expect(lint, reason = "...")]` (unfulfilled-expectation warning
    built in, but for Clippy lints only when Clippy runs; see 4.3) plus
    `clippy::allow_attributes_without_reason` and `clippy::allow_attributes`
    (both restriction group, so off unless enabled).
  - *C++:* an owned equivalent. A reasoned suppression marker the verbs checker
    reads, reports when it suppresses nothing, and counts per change.
- **Evidence.**
  - *Stale suppressions are the norm:* 50.8% of human suppressions suppress
    nothing in 10 Pylint projects (4.3).
  - *A cheap path gets used:* an agent pipeline offered a suppress path sent
    30.4% of SonarQube warnings through it (4.3a).
  - *Agents bypass under pressure:* AdaTrans; ImpossibleBench; the blackbird
    R2 episode (4.2).
  - *Reasons do not prove necessity:* in R2 the reasons were present and the
    bypass was still avoidable. A reason makes a bypass *reviewable*; it does
    not make it *right*.
- **Costs.** Low for Rust (native); moderate for C++ (owned marker parsing and
  staleness detection).

### 7.7 Seeded-fault testing beyond the guards → class T (option, not a habit)

The largest class (T, 22) is weak test oracles. Banik's 80.2% (2.3) shows the
same thing at scale.

- *No construct fixes this.*
- *Seeded-fault machinery is relevant anyway.* It runs a seed, then asks whether
  the checker fires. Asking whether the project's *tests* fail as well is the
  mutation-testing question. Google's practice (feedback lane §5) shows it
  works on changed code.
- *Scope.* Whether verbs owns that is a scope question (Open questions).

---

## 8. What this means for verbs

### 8.1 Options, ranked

1. **State machine habit with absorbing terminals and generation-checked
   completions.**
   - *Why first:* it is the largest construct-addressable class in the record
     (15/125) and carries high severity.
   - *Shape:* async, callback-driven native code, which is where agents are
     least supervised by tests (error paths 81–86% untested, 2.3).
   - *Seeds:* direct state writes and late-completion overwrites are simple to
     seed and to detect.
   - *Weakness:* there is no published precision evidence for any nudge that
     *finds* unencoded state machines, and verbs' own enum-candidate heuristic
     reached only 46–62%. So the stop (bypass of the construct) is strong; the
     nudge is speculative.
2. **Way past with a reason, with staleness detection, as shared machinery.**
   - *Why:* every habit needs it.
   - *Evidence:* staleness is the common case (50.8%), and agents bypass under
     pressure.
   - *Per language:* Rust gets it nearly free; C++ must own it. Rank it second
     only because it is infrastructure, not a habit.
3. **Strong identifiers, plus a captured-origin construct.**
   - *Why:* this is the only habit with *field evidence that agents comply*:
     at least 10 swappable-parameter stops, each fixed without suppression,
     mostly by a named type. The stop already exists in clang-tidy; Rust has no
     Clippy equivalent, so the Rust stop is owned work (Rice 2017 gives a
     measured call-site design to study).
   - *New part:* captured origin targets the record's I findings (one High, one
     P1) that no existing check names.
4. **Bounded and refined numbers.**
   - *Why:* the strongest literature support for C++ (overflow and OOB dominate
     confirmed runtime faults in LLM C++).
   - *Rank:* fourth because the operator's C++ record shows few N findings, and
     because generic arithmetic lints are notoriously noisy.
   - *Most precise slice:* the shared-limit and finite-float slice. It has the
     fewest firing sites and matches concrete findings.
5. **Closed sum types and strict parsing.** Small but precise class in the
   record (7, about 6 rejectable). Native in Rust; the serde sequence-form and
   `as_str()` traps are Rust-specific stops worth having.
6. **Obligation token / owned resource.** Real faults (E 13, R 5), but only
   partly encodable, and C++ lacks linear types. Worth a habit for the
   kill-on-drop child and the must-consume terminal. The broader "commit point"
   property stays with review.
7. **Mutation testing of the project's own tests** (class T). Outside the
   habit model, but it addresses the largest single class and reuses the seeding
   machinery. List it as a scope option, not a habit.

### 8.2 What not to build

- **Compile errors agents already hit.** Hallucinated APIs, type mismatches and
  borrow errors are stopped by the compiler. Verbs' job there is only to stop
  the escape hatches (`unsafe`, casts, NOLINT, `#[allow]`).
- **Generic warning counts as a quality signal.** They track code volume
  (Mahmud, He). They should not be a verbs output.

---

## 9. Open questions the design must settle

1. **Nudges that find unencoded constructs.** Does verbs ship nudges that
   *discover* where a construct should be ("these bools are a state machine")?
   Or only stops on misuse and bypass of constructs already used? The evidence
   supports the second; the first has a measured 46–62% precision ceiling in
   this repository.
2. **Captured origin.** Is it a habit of its own, or a property of the
   state-machine habit (late completions carry the generation)? The record
   splits the same faults both ways.
3. **Reason quality.** What counts as an acceptable reason at a way-past? R2
   shows reasoned suppressions that review still rejected. Is "reason present
   and suppression still fires" enough, or does verbs report suppression counts
   per change for review?
4. **C++ staleness.** How does C++ detect a stale reason without clang-tidy
   support? (Checked: clang-tidy 23.1.2 cannot report unused NOLINTs; see 4.3.
   The open part is the design of the owned marker and where it runs.)
5. **Test oracles.** Does verbs own any test-oracle check (class T, 22/125), or
   leave it to the project's mutation testing?
6. **Seed realism.** Which seed source decides "the guard works": scripted
   habit-shaped seeds (section 6 table), BugPilot-style natural faults, or both
   with separate reporting?
7. **Choosing a corpus.** The record's class mix depends on code kind (protocol
   code gives S/I/E; numeric code gives N). Which corpus projects represent the
   operator's own code for seeded-fault runs? `context/corpus/probe.tsv` lists 32
   that configure.
8. **Partial encodings.** How does verbs report a habit whose construct only
   partly encodes the discipline? Examples: "commit point", or the bounded type
   that makes overflow loud but not right. Is that a stop, a nudge, or
   documentation?
9. **Second rater.** Section 5's classification has one rater. Should a second
   independent classification of the same 125 findings be done before habit
   priorities are fixed?

---

## Acquired PDFs (papers/)

| File | Source |
| --- | --- |
| tambon-2025-bugs-in-llm-generated-code-emse.pdf | arXiv:2403.08937 |
| wang-2025-code-generation-errors-characteristics-icse.pdf | arXiv:2406.08731 |
| nogueira-2026-unreliable-in-practice-llm-code-errors.pdf | arXiv:2608.00661 |
| he-2026-cursor-speed-at-cost-of-quality-msr.pdf | arXiv:2511.04427 |
| agarwal-2026-ai-ides-or-autonomous-agents.pdf | arXiv:2601.13597 |
| chen-jiang-2025-agent-patch-patterns-code-quality.pdf | arXiv:2410.12468 |
| dipongkor-2026-test-coverage-agentic-prs-icsme.pdf | arXiv:2607.18057 |
| ehsani-2026-where-do-ai-coding-agents-fail.pdf | arXiv:2601.15195 |
| banik-2026-all-smoke-no-alarm-agent-test-oracles.pdf | arXiv:2606.18168 |
| hu-2025-suppressed-static-analysis-warnings-fse.pdf | people.ece.ubc.ca/mjulia/publications/Suppressed_Static_Analysis_Warnings_FSE2025.pdf |
| jesse-2023-llms-simple-stupid-bugs-msr.pdf | arXiv:2303.11455 (added in check) |
| rice-2017-detecting-argument-selection-defects-oopsla.pdf | cl.cam.ac.uk/~acr31/pubs/rice-defects.pdf (added in check) |
| szalay-2020-implicit-conversions-argument-swapping-scam.pdf | conferences.computer.org SCAM 2020, 924800a192.pdf (added in check) |

Web-only (search-level, not downloaded): arXiv:2605.22534 and arXiv:2606.13468
(agent PR rejection); SafeTrans arXiv:2505.10708; SACTOR arXiv:2503.12511;
arXiv:2511.20617; arXiv:2602.00840; Zhu et al. arXiv:2605.02741 (smells in
LLM and multi-agent Python).

---

## Check (2026-11-23)

Checker pass on this report. Every claim below was checked by opening the
source: PDFs via `pdftotext`, the operator's repositories read-only at the
commits named in 5.1, the quarantined LLVM 23.1.2 source, and the installed
toolchains (Homebrew clang-tidy 23.1.2, rustc 1.99.0, clippy 0.1.99).

### Verified as written

- **Tambon (1.1).** Table 2 shares, 333 samples, 34 survey respondents; 62.16%
  single-label (so 37.8% multi-label, §4.1.2); missing corner case is the only
  pattern rated hard to diagnose (§4.2.3).
- **Wang ICSE 2025 (1.2).** 557 solutions, six models, seven semantic
  categories, Finding 2 (over 40% missing or incorrect code block).
- **Nogueira (1.3).** 86,726 errors, 1,651 problems, 7 models, classifier
  accuracy 0.81–0.92 (Table IV); Table VI compile shares; Table X runtime
  shares for out of bounds, overflow and input processing; up to two feedback
  generations; the paper's own panic-vs-silent overflow reading (§IV-B).
- **Mahmud (1.4).** 9.3% vs 2.6%; OR 2.15 (1.52–3.03); cppcheck OR 0.68
  (0.57–0.81); CWE-190 then CWE-122/121; static CWEs 398/563/570/571.
- **Mündler (1.5).** 94% type-check, 6% syntax (§1).
- **He (2.1)** Table 2 numbers and Table 8 category deltas; **Agarwal** ~18% and
  ~39% (abstract, Table 2); **Chen & Jiang (2.2)** 4,892 patches, 10 agents, zero
  vulnerabilities; **Banik (2.3)** 86,156 / 33,596 / 2,807 / 80.2% / OR 1.28;
  **Dipongkor** 4,882 PRs, 61.5% / 27.0%, 86.0% / 81.0%; **BugPilot (2.4)**
  categories C, F, G and the Figure 4 caption; **arXiv:2605.22534** 35.7%
  (abstract, now read); **arXiv:2606.13468** 46.41% rejection, 14 reasons, no
  code-fault taxonomy (abstract, now read).
- **Hu (4.3).** 7,357 suppressions in 46 Python projects; 50.8%; reasons list.
- **Feedback-lane numbers** used here (ImpossibleBench 33%→38%, PatchDiff
  29.6%, Just 2014 27%, Multi-SWE-bench C++ 0–11.63%, AdaTrans quote).
- **Operator record.** Blackbird `.clang-tidy` at `afacae8` (five checks plus
  `clang-analyzer-*`, `WarningsAsErrors: '*'`); R2 text at
  `raw-partition-claim-code-review.md:28-34`; `JOURNAL.md` lines 6595,
  6622-6624, 5809, 73-79, 7574-7578, 11975-11977; all ten swappable-parameter
  lines; the five unchecked-optional lines; `grep -ci weaken` = 18. Spot-checked
  12 classified findings against their reviews (native-apparatus 1–3, E-01..E-03,
  CT-01/CT-02, CA-01..CA-04, D1 `poisoned`, command-live 2, task-owner §1,
  raw-instrumentation 300/256 KiB, authored-raw destruction order, u1-head F1,
  NC-3); content and cited severities matched. Class-count arithmetic checked:
  rows, per-project rows and the 84/41 language split all sum to 125.
- **Rust 1.81** stabilized `#[expect]` (release post, accessed 2026-11-23).

### Corrected (old -> new, source)

1. **Nogueira runtime bearing (1.3).** "The two biggest runtime classes are
   range faults" -> true for Rust (44.0% overflow, 28.1% OOB); in C++ the next
   classes after OOB (60.0%) are out of memory 10.7% and recursion 8.0%, and
   overflow is 3.8%. Source: Table X. Rows for OOM and recursion added.
2. **Nogueira feedback reading (1.3, 4.1).** "Raw compiler feedback fixes only
   7.8% of parameter-type errors ... a weak repair signal" -> the error
   disappears in 66.3% of cases (58.5% partially fixed + 7.8% fixed); 7.8% is
   the share that then passes all tests. Lesson changed to "a cleared stop is
   not evidence the fault is gone." Source: Table VIII and its definition of
   fixed/partially fixed (§IV).
3. **He et al. robustness (2.1).** "+30% warnings, +41% complexity", strength S
   -> same Borusyak estimates, but Callaway–Sant'Anna gives −10.49% and −3.80%
   (not significant), so strength M. "The categories that grew are not bug
   categories" -> the largest growth was non-bug; type safety, logic error,
   security and error handling also rose, by less. Table 8 is a convenience
   sample with an LLM-assisted taxonomy. Source: Appendix B robustness table and
   text, Appendix D.
4. **Hu et al. scope (4.3).** "50.8% of all suppressions" across Pylint,
   Checkstyle, PMD, ESLint -> 50.8% measured on 10 Pylint projects;
   Checkstyle/PMD/ESLint data come from 46 student projects. Strength S -> M.
   Source: Hu §1 (RQ3), §2.2.
5. **clang-tidy unused NOLINT (4.3, Open question 4).** "No unused report that I
   know of. Verify" -> verified: none in clang-tidy 23.1.2. Sources:
   `NoLintDirectiveHandler.cpp:181-193` (only unmatched BEGIN/END),
   `clang-tidy --help` of the pinned binary, `docs/clang-tidy/index.rst:541`
   (reason optional); `[[clang::suppress]]` is analyzer-only (`Attr.td:3496`,
   `AttrDocs.td:6632`).
6. **Rust `#[expect]` staleness (4.3, 7.6).** "Rust already reports it" -> only
   under the tool that owns the lint: rustc 1.99.0 reported a stale
   `#[expect(unused_variables)]` but not a stale
   `#[expect(clippy::needless_return)]`; clippy-driver 0.1.99 reported both.
   Source: a two-function test file compiled with each driver in the checker's
   scratch directory.
7. **Swappable-parameter fixes (4.4).** "Every recorded fix introduced a named
   type or struct" -> 7 named types or aggregates, 2 compile-time widths, 1
   narrowed constructor, 1 helper cut to one parameter; an 11th stop at
   `JOURNAL.md:7188`. Source: `JOURNAL.md` lines 1072-1076, 1343-1346, 2237-2239,
   6614-6618, 7187-7190, 9292-9295, 9945-9949, 10518-10520, 11576-11581,
   12510-12514, 12594-12597.
8. **Surviving suppressions (4.4).** "No suppressions survived" -> two test-only
   `NOLINTNEXTLINE(bugprone-use-after-move,clang-analyzer-cplusplus.Move)` at
   `blackbird/tests/foundation_test.cpp:138,140`, added `017e671` and recorded
   at `JOURNAL.md:1075-1076`. R2 itself refers to them as "existing historical
   annotations".
9. **Rust severity (5.2).** "Of the four High Rust findings" -> scales differ by
   project; deleuze's Critical J1 (`read-gate-code-json.md:45`, class L) was
   omitted.
10. **Clippy swappable equivalent (7.2).** "I know of no Clippy equivalent.
    Verify" -> verified none in clippy 0.1.99's lint list (`clippy-driver -W
    help`).
11. **Swappable precision (7.2).** "Precision: none measured" -> the clang-tidy
    check is an interface rule with published report counts (Szalay 2020 §V,
    40% fewer reports with relatedness heuristics); the call-site name-based
    form has measured precision (Rice 2017: 85% at high threshold, 459 TP / 78
    FP).
12. **Mahmud models (1.4).** "Small open models" -> Gemma 3 27B, LLaMA 3.3 70B,
    Qwen 2.5 Coder 32B (mid-size, open-weight). Added: 1.8% of test-passing AI
    programs still trigger sanitizers.
13. **Population caveat (5.1).** Not a correction of counts but of
    reproducibility: oxcart's glob gives 56 files (not 49) and deleuze's gives 9
    `*code*` files, 6 with finding lists (not 5). Selection rules as stated do
    not reproduce; class counts remain the lane's.

### Added

- **2.6:** Jesse et al. MSR 2023 (LLMs write known single-statement bugs about
  2x as often as fixes; SStuB templates as a seed set); RobustAPI (62% API
  misuse for GPT-4, abstract); Zhuo et al. 2025 API-misuse taxonomy; Pearce et
  al. S&P 2022 (~40% of Copilot programs vulnerable).
- **4.3a:** CodeCureAgent (FSE 2026): an agent pipeline suppressed 30.4% of
  1,000 SonarQube warnings as false positives; 81.0% classification accuracy on
  true false positives.
- **4.3:** Prior art for staleness reports in other ecosystems (ESLint
  `reportUnusedDisableDirectives` default `"warn"` with `--` reasons; mypy
  `warn_unused_ignores`; Pylint `useless-suppression`).
- **7.2:** Rice 2017 and Szalay 2020 as precision and design sources for the
  strong-identifier stop and a possible Rust call-site nudge.
- **7.5:** `clippy::zombie_processes` (warn by default) as an existing partial
  stop for the `Child` case, with its documented same-body limit.
- **4.4:** the observation that both blackbird suppression episodes were in
  negative tests that deliberately exercise a construct's forbidden use; that
  is where a way past is genuinely needed.

### Still open after the check

- Second rater for the 125 findings, and a reproducible statement of the oxcart
  and deleuze selection rules.
- Full text of RobustAPI (arXiv:2308.10335) and Pearce 2022 (only abstracts
  read); SafeTrans, SACTOR and the Clippy-idiomaticity papers remain
  search-level.
- Szalay, Sinkovics, Porkoláb, JSS 181 (2021) 111048, "Practical heuristics to
  improve precision for erroneous function argument swapping detection in C and
  C++": not obtained; it is the follow-up with the check's precision heuristics.
- No study found of agents adding `NOLINT`, `#[allow]`, `as any` or
  `# type: ignore` in real PRs; mining AIDev diffs for added suppression tokens
  would answer it.
