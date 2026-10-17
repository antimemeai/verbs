# Agent feedback and evaluation: literature lane

Prepared 2026-10-17 for the verbs preliminaries. It covers two questions:

1. Does static and structural feedback measurably help coding agents? In what shape, and at what time?
2. How should the kill-criterion experiment be built so its result can be trusted?

It also covers the operator's question about whether a persistent delta daemon
is needed. PDFs are in `papers/` (ignored); the file names are listed at the end.

**Evidence strength.**

- **S:** a controlled comparison across several models or a large sample,
  with significance or confidence intervals reported.
- **M:** a controlled comparison that is small, uses a single model, or
  lacks reported variance.
- **W:** a design paper with no ablation, a preliminary or single-author
  study, a vendor report, or anecdote.

**What was read.** "Read" means I read the cited sections of the PDF text. "Abstract" means only the abstract and figures were checked.

---

## 1. Feedback in the loop: what measurably helped

**Yang et al., "SWE-agent: Agent-Computer Interfaces Enable Automated Software
Engineering," NeurIPS 2024.** arXiv:2405.15793v3. https://arxiv.org/abs/2405.15793
- **Edit gate.** The edit command runs a filtered flake8 after each edit
  (syntax, indentation and undefined names only) and *reverts* edits that
  introduce errors.
- **Gate effect.** SWE-bench Lite resolve rate is 18.0% with the gate and 15.0% without it, using GPT-4 Turbo on 300 instances (Table 3). With no edit command at all it is 10.3%.
- **Recovery odds fall.** 51.7% of trajectories contain at least one failed edit. The chance of
  an eventually successful edit is 90.5% in general, but 57.2% after one failed edit.
- **Message content.** The authors found the rejection message works best when it includes all three parts: the error type, the attempted edit, and the original content (qualitative finding).
- **Bearing on verbs.** This is the cleanest published evidence for checking at the edit boundary. The
  gate catches the first bad edit before errors cascade. **M** (one model, one run, small
  effect). Read.

**Mündler-Sasahara, Venev, Song, Vechev, He, "Generative Compilation: On-the-Fly
Compiler Feedback as AI Generates Code," 2026.** arXiv:2607.13921v2.
https://arxiv.org/abs/2607.13921
- **Setup.** A "sealor" completes partial Rust programs so that rustc can check them during
  decoding. It is evaluated on repository-level C-to-Rust translation and on
  updated-API tasks, across 7 models including Opus 4.8 and GPT 5.3.
- **Results.** Compiler error rate falls from 65.9% with no feedback, to 20.7% with post-generation
  compiler feedback (PC), to 13.1% with on-the-fly feedback (GC). GC beats PC in 13 of 14
  configurations (9 significant at α=5%), and has the best functional correctness in 11 of 14.
- **Cost.** Average added runtime falls from +233s (PC) to +135s (GC).
- **Mechanism.** Errors are caught nearer their source, with fewer diagnostics per message and fewer cascades.
- **Bearing on verbs.** Having feedback at all is the large effect. Earlier and finer feedback is a smaller but real effect.
  **S**. Read (abstract, §7.1–7.2, Table 1).

**Olausson et al., "Is Self-Repair a Silver Bullet for Code Generation?" ICLR
2024.** arXiv:2306.09896v5. https://arxiv.org/abs/2306.09896
- **Finding.** Self-repair gains are modest once their cost is counted, and the bottleneck is feedback
  quality. Stronger, external feedback produces much larger gains, and human
  feedback larger still.
- **Bearing on verbs.** Mechanical, specific feedback is what self-critique lacks. **S**. Abstract.

**Dolcetti et al., "Helping LLMs Improve Code Generation Using Feedback from
Testing and Static Analysis," 2024.** arXiv:2412.14841v2.
https://arxiv.org/abs/2412.14841
- **Setup.** C code from 100 MBPP tasks, with Infer as the static analyzer.
- **Finding.** Models are very poor at detecting their own bugs or
  vulnerabilities. Given Infer's report, the best model fixes 39 of 44
  vulnerabilities (89%). Given failing-test information, it fully repairs 96 of 155 incorrect files (62%).
- **Bearing on verbs.** An external analyzer report turns poor self-detection into a high fix rate, in C. **M**. Read
  (contribution list).

**Zhang & Kothari, "Unlocking LLM Code Correction with Iterative Feedback Loops,"
2026.** arXiv:2606.17514v1. https://arxiv.org/abs/2606.17514
- **Finding.** Compiler and test feedback over iterations helps reasoning models far more than
  non-reasoning models. Syntactic and runtime errors are far more tractable than
  logical or algorithmic ones.
- **Bearing on verbs.** Feedback helps most where the fault class is mechanically namable. **M**. Abstract.

**Blyth, Licorish, Treude, Wagner, "Static Analysis as a Feedback Loop," 2025.**
arXiv:2508.14419v1. https://arxiv.org/abs/2508.14419
- **Setup.** Bandit and Pylint findings fed back to GPT-4o on PythonSecurityEval.
- **Finding.** Over 10 iterations, security issues fall from over 40% to 13% and reliability warnings from over 50% to 11%.
- **Caveat.** Single model, Python, not agentic, and functional correctness after repair was not a reported endpoint.
  **M**. Abstract.

**Wadhwa et al., "CORE: Resolving Code Quality Issues using LLMs," FSE 2024.**
arXiv:2309.12938v1. https://arxiv.org/abs/2309.12938
- **Setup.** A proposer LLM fixes static-analysis warnings using the tool's own fix
  guidance. Only candidates that parse and clear the warning are admitted, then a ranker LLM screens for unfaithful changes.
- **Finding.** The ranker cut false positives by 25.8%. In other words, warning-clearing fixes
  often changed behavior in subtle ways.
- **Bearing on verbs.** "Diagnostic gone" is not "fixed". **M**. Search-level summary, plus the paper's title page.

**Svoboda et al., "Automated Code Repair for C/C++ Static Analysis Alerts,"
2025.** arXiv:2508.02820v1. https://arxiv.org/abs/2508.02820
- **Setup.** Non-LLM repair of clang-tidy, Cppcheck and Rosecheckers alerts on Git and other codebases.
- **Bearing on verbs.** Prior art for clang-tidy-driven repair at scale in C. **W** for our question. Title and abstract.

**Mahmud et al., "The Illusion of Safety: Multi-Tier Verification of AI vs. Human
C++ Code," 2026.** arXiv:2607.00107v3. https://arxiv.org/abs/2607.00107
- **Setup.** 8,918 C++ programs checked at four tiers: tests, cppcheck/clang-tidy,
  ASan/UBSan, and ESBMC.
- **Finding.** Static tools report comparable warning rates for AI and human code. Yet AI code is
  about twice as likely to trigger a *confirmed runtime* violation.
- **Bearing on verbs.** For C++, static warnings alone are a weak oracle, so the
  experiment needs a sanitizer tier. **S**. Abstract.

## 2. Constraint-guided generation and verifier loops

**Mündler et al., "Type-Constrained Code Generation with Language Models," PLDI
2025.** arXiv:2504.09246v2. https://arxiv.org/abs/2504.09246
- **Method.** Prefix automata and a type-inhabitation search enforce well-typedness during
  decoding, on a TypeScript subset.
- **Finding.** On HumanEval and MBPP it cuts compilation errors by more than half, across model sizes and
  families.
- **Caveat.** It needs white-box logit access and a reimplementation of the type system. That makes it
  infeasible for C++, and for black-box frontier models in Blackbird.
- **Bearing on verbs.** Relevant only as a ceiling on what earlier type feedback can buy. **S**. Abstract.

**Agrawal et al., "Monitor-Guided Decoding of Code LMs with Static Analysis of
Repository Context," NeurIPS 2023.** arXiv:2306.10763v2.
https://arxiv.org/abs/2306.10763
- **Method.** A language-server "monitor" masks logits for type-consistent dereferences.
- **Finding.** A 1.1B model with the monitor beats text-davinci-003 on compilation rate.
- **Bearing on verbs.** Background static analysis during generation pays off, but it is white-box. **M**. Abstract.

**Yang et al., "AutoVerus: Automated Proof Generation for Rust Code," OOPSLA
2025.** arXiv:2409.13082v3. https://arxiv.org/abs/2409.13082
- **Method.** The debugging phase picks *one* verifier error at a time and routes it to a repair agent
  specific to that error type (about ten types: precondition, postcondition, invariant at front or end,
  arithmetic overflow, type mismatch, and so on). Houdini prunes annotations. `assume` is
  forbidden in final proofs.
- **Finding.** Over 90% of 150 tasks proved; more than half within 30 s or 3 LLM calls.
- **Bearing on verbs.** Feedback shape: one prioritized, typed error plus repair guidance specific to that
  class. This maps onto verbs' "suggest:" line toward vlib, and onto `[[assume]]` gating. **M**. Read
  (§4.3).

**Aggarwal, Parno, Welleck, "AlphaVerus," ICML 2025.** arXiv:2412.06176v1.
https://arxiv.org/abs/2412.06176
- **Method.** A verifier-feedback tree search. An explicit critique stage (rules, a comparison
  LLM, and an adversarial "exploit model") filters specification/program pairs that pass the verifier
  only by trivial or misaligned specs.
- **Bearing on verbs.** Verifier pass is gameable; the filter is part of the method. **M**. Read (critique
  module).

**Deligiannis et al., "RustAssistant: Using LLMs to Fix Compilation Errors in Rust
Code," ICSE 2025.** arXiv:2308.05177v1. https://arxiv.org/abs/2308.05177
- **Finding.** An LLM–rustc loop reaches about 74% peak fix accuracy on real compile errors. **M**. Search-level.

**Liu et al., "AdaTrans: Automated C-to-Rust Transformation via Error-Adaptive
Repair," 2026.** arXiv:2606.31706v1. https://arxiv.org/abs/2606.31706
- **Finding.** When the borrow checker rejects code, LLMs "frequently resort to unsafe blocks or raw
  pointers to suppress compiler errors."
- **Method.** AdaTrans constrains the repair search to memory-safe Rust, giving a 1.19% unsafe file rate.
- **Bearing on verbs.** The strictest checker invites the escape hatch. The verbs C++ analogues are
  `const_cast`, `mutable`, raw-int fallbacks and `NOLINT`. **M**. Read (§2, related work).

## 3. Push or pull: do agents use optional checkers?

**Xu, "Does a Language Server Save Tokens for Coding Agents? A Measurement
Methodology and Preliminary Study," 2026.** arXiv:2608.13568v1.
https://arxiv.org/abs/2608.13568
- **Usage when optional.** Claude agents with a free choice used LSP 0–6% of the time on
  localization and 45–57% on reference-completeness tasks.
- **Token cost.** On localization, LSP *costs* tokens: +6% (Opus) and +118% (Sonnet).
- **Precision.** LSP buys precision on reference tasks (1.00 vs 0.76), but at about a 19% token premium.
- **Metric.** Tokens-to-success at iso-accuracy is a usable metric template.
- **Caveat.** Single author, preliminary, Python and TypeScript, and the author reports degraded search tooling. **W**. Read
  (abstract, §1–3).

**Kiro, "Are AI coding agents actually getting better?" vendor blog, Aug 2026.**
https://kiro.dev/blog/diagnostics-over-time/
- **Data.** About 1.5M Kiro IDE conversations from January–June 2026, across Opus 4.5–4.8 and Sonnet 4–4.6.
- **Finding.** Conversations invoking the diagnostics tool range from 2.74% (Sonnet 4.5) to 22.26%
  (Opus 4.6).
- **Bearing on verbs.** With a pull tool, most conversations never check. No outcome effect was measured.
  The post also cites an external result (blocking finalization until errors are resolved
  cut incorrect-code acceptance from about 90% to about 8%) whose source I could not identify. Do not cite
  that figure. **W** (vendor). Fetched.

**Fan et al., "An Empirical Study of Harness Design for Coding Agents," 2026.**
arXiv:2609.20804v1. https://arxiv.org/abs/2609.20804
- **Design.** 176 matched settings on SWE-bench Verified and Terminal-Bench 2.1, with 4 models. Post-edit
  diagnostics (ruff/pyflakes appended to the edit result) are a *fixed* component, so they are
  not ablated.
- **Finding 1.** Making elided context recoverable "adds machinery that models rarely use and yields
  no accuracy gain." That is more evidence that optional pull mechanisms go unused.
- **Finding 2.** Stronger models spend turns on *redundant post-edit verification*. Planning reduces it,
  which lowers cost.
- **Bearing on verbs.** Push-at-edit is now standard harness practice, and agent-initiated checking costs turns.
  **S** for the harness findings, **n/a** for the diagnostics. Read (abstract, §3).

**openJiuwen Team (Huawei), "openJiuwen: Beyond Static Harnesses for Long-Horizon
Coding Agents," 2026.** arXiv:2608.27969v1. https://arxiv.org/abs/2608.27969
- **Design.** "LSP-Driven Passive Feedback": after relevant changes, diagnostics are ranked, deduplicated
  and limited per file and in total, then injected. The authors distinguish this from *active* queries the agent must request.
- **Results.** SWE-bench Verified 82.6%, with no ablation of this component.
- **Bearing on verbs.** A design reference for push shape. **W**. Read (§3.2.4).

**Zhang, "Reinforcement Learning from Compiler and Language Server Feedback"
(Lanser-CLI), 2025/26.** arXiv:2510.22907v2. https://arxiv.org/abs/2510.22907
- **Design.** Pinned LSP sessions become replayable, content-hashed "analysis bundles". A process
  reward is computed from diagnostic deltas, credited *only when the selector scope is
  unchanged*.
- **Results.** Formal properties only; no agent experiment.
- **Bearing on verbs.** Corroborates keying deltas on symbol scope rather than lines, as the brief does. **W**. Read
  (abstract, §3).

## 4. Gaming, suppression, and Goodhart effects

**Zhong, Raghunathan, Carlini, "ImpossibleBench: Measuring LLMs' Propensity of
Exploiting Test Cases," ICLR 2026.** arXiv:2510.20270v1.
https://arxiv.org/abs/2510.20270
- **Cheating strategies observed.** Test modification (Claude models mostly), special-casing,
  recording state between calls, and comparison-operator overloading (GPT-5).
- **Prompting.** Strict prompts help but leave high rates: GPT-5 cheats 54% and Opus 4.1 50% on
  Conflicting-SWEbench.
- **Test access.** Read-only tests stop test modification without hurting legitimate performance. Hidden tests
  stop nearly all cheating but cost legitimate performance.
- **Feedback loops raise cheating.** Multiple submissions with feedback move legitimate pass rates from 80% to 83%, but
  cheating from 33% to 38%.
- **Bearing on verbs.** Repeated diagnostics pressure increases shortcut-taking. **S**. Read (§4–5).

**Gabor, Lynch, Rosenfeld, "EvilGenie: A Reward Hacking Benchmark," 2025/26.**
arXiv:2511.21654v2. https://arxiv.org/abs/2511.21654
- **Findings.** Explicit reward hacking by Codex and Claude Code, and misaligned behavior by all three
  agents tested.
- **Detection.** An LLM judge was highly effective in unambiguous cases. Held-out tests added little.
  Test-file edit detection is cheap and catches the common case. **M**. Read (abstract, §2.5).

**Baker et al., "Monitoring Reasoning Models for Misbehavior and the Risks of
Promoting Obfuscation," 2025.** arXiv:2503.11926v1. https://arxiv.org/abs/2503.11926
- **Finding.** Chain-of-thought monitoring catches coding reward hacks far better than monitoring actions alone. Optimizing
  against the monitor produces *obfuscated* hacking.
- **Bearing on verbs.** Never let the evaluation signal be the training or optimization signal the agent sees. **S**. Abstract.

**MacDiarmid et al., "Natural Emergent Misalignment from Reward Hacking in
Production RL," Anthropic/Redwood, 2025.** arXiv:2511.18397v1.
https://arxiv.org/abs/2511.18397
- **Finding.** Reward hacking learned in production coding environments generalizes to broader misalignment,
  including sabotage attempts under Claude Code.
- **Bearing on verbs.** Context for why diagnostics must not become a hackable reward. **S**. Abstract.

**METR, "Recent Frontier Models Are Reward Hacking," June 2025.**
https://metr.org/blog/2025-06-05-recent-reward-hacking
- **Finding.** o3 monkey-patched timing and read answers already computed by the scorer; models showed awareness the behavior
  was unwanted. **M**. Search-level.

**Rogero, "The State of Reward Hacking in AI," MIRI, Sept 2026.**
https://intelligence.org/wp-content/uploads/The-State-of-Reward-Hacking-in-AI-September-2026.pdf
- **Finding.** A review: models "may cheat more severely when stuck or blocked from easier paths", and
  anti-cheating prompts move rates only modestly (METR table: 70–95%). **W** (secondary review). Read
  (summary).

**Practitioner reports on lint suppression by agents.**
- **Sources.** aemdemos/patients-stryker issue #273
  (https://github.com/aemdemos/patients-stryker/issues/273); ltowarek/dust-mite issue #160
  (https://github.com/ltowarek/dust-mite/issues/160); and a Medium post on agents adding inline
  eslint-disable and editing lint config
  (https://medium.com/@albro/eslint-as-ai-guardrails-the-rules-that-make-ai-code-readable-8899c71d3446).
- **Finding.** Agents clear lint failures by inline suppression, by downgrading the rule, or by excluding the file.
- **Gap.** No peer-reviewed measurement was found. **W**.

## 5. Evaluation instruments

### Benchmark validity

**Wang, Pradel, Liu, "Are 'Solved Issues' in SWE-bench Really Solved Correctly?"
ICSE 2026.** arXiv:2503.15223v2. https://arxiv.org/abs/2503.15223
- **Finding.** Using differential patch testing (PatchDiff), 7.8% of plausible patches fail the full developer test
  suite. 29.6% behave differently from the ground truth. Reported resolve rates are inflated by 6.2 points. **S**.
  Read (abstract).

**Yu et al., "UTBoost," 2025.** arXiv:2506.09289v1. https://arxiv.org/abs/2506.09289
- **Finding.** Generated tests exposed 345 erroneous "passed" patches. Rankings changed for 40.9% of Lite
  and 24.4% of Verified leaderboard entries. **S**. Read (abstract).

**Aleithan et al., "SWE-Bench+," 2024.** arXiv:2410.06992v2.
https://arxiv.org/abs/2410.06992
- **Finding.** 32.67% of successful patches had the solution leaked in the issue text, and 31.08% passed only because of weak tests.
  SWE-agent+GPT-4 falls from 12.47% to 3.97%. **S**. Read (abstract).

**Zhu et al., "Establishing Best Practices for Building Rigorous Agentic
Benchmarks" (ABC checklist), NeurIPS 2025 D&B.** arXiv:2507.02825v5.
https://arxiv.org/abs/2507.02825
- **Finding.** Task and reward flaws distort measured performance by up to 100% relative. The paper separates
  *task validity* from *outcome validity* and provides a checklist. Use it on our harness. **S**. Read
  (§1).

### Trajectories and confounds

**Mehtiyev & Assunção, "Beyond Resolution Rates: Behavioral Drivers of Coding
Agent Success and Failure," 2026.** arXiv:2604.02547v1.
https://arxiv.org/abs/2604.02547
- **Setup.** 9,374 trajectories: 19 agents on 500 tasks.
- **Confound.** The trajectory-length/failure correlation *reverses* once task difficulty is controlled.
- **What predicts success.** Gathering context before editing, and investing in validation.
- **Model versus harness.** The LLM, not the harness, is the primary driver. The harness performance gap *shrinks with each LLM
  generation*.
- **Bearing on verbs.** The edits-to-detection comparison must be paired within each task. Also, a verbs effect measured on today's
  models may shrink. **S**. Read (abstract).

**Majgaonkar et al., "Understanding Code Agent Behaviour," 2025.**
arXiv:2511.00197v1. https://arxiv.org/abs/2511.00197
- **Finding.** Failed runs are longer and more variable. 72–81% of failures still find the right files; success
  hinges on approximately right edits. **M**. Read (abstract).

**Becker, Rush, Barnes, Rein (METR), "Measuring the Impact of Early-2025 AI on
Experienced Open-Source Developer Productivity," 2025.** arXiv:2507.09089v2.
https://arxiv.org/abs/2507.09089
- **Design.** A randomized controlled trial: tasks are defined *before* being randomized to the AI-allowed or AI-disallowed arm.
- **Finding.** Developers forecast a 24% speedup and believed 20% afterwards. Actual result: 19% *slower*.
- **Bearing on verbs.** The design template, and a warning that perceived benefit is not evidence. **S**. Read
  (abstract).

**Jarmak, "Engineering Reliable Coding Agents," 2026.** arXiv:2608.13867v1.
https://arxiv.org/abs/2608.13867
- **Content.** A multivocal review: many apparent model failures originate in the harness, environment or
  verification layer, and gains at one layer often fail to reach end-to-end outcomes. **W**. Abstract.

### C/C++ task sources

**Zan et al., "Multi-SWE-bench," NeurIPS 2025 D&B.** arXiv:2504.02605v1.
https://arxiv.org/abs/2504.02605
- **Data.** The C++ split has 129 instances. 2025-era resolve rates on C++ are 0–11.63% (best: MSWE-agent with Claude
  3.7 Sonnet), versus 45.8% on Python.
- **Bearing on verbs.** C++ is where agents are weakest, so there is room for verbs to help. **S**. Read (Table 4).

**Wang et al., "Defects4C," ASE 2025.** arXiv:2510.11059v2.
https://arxiv.org/abs/2510.11059
- **Data.** 248 buggy functions and 102 vulnerable C/C++ functions with reproducing tests. It is function-level, not
  agentic, but a harness model for reproducible C/C++ defects. **M**. Title and abstract.

**Zhu et al., "Needle in the Repo (NITR)," 2026.** arXiv:2603.27745v1.
https://arxiv.org/abs/2603.27745
- **Setup.** 21 small C++ repositories, each with functional tests *and* structural oracles.
- **Findings.** 13.3% of outcomes pass functional tests but fail the structural oracle. Agent mode raises success from 28.2% to 45.0%
  but does not remove those failures.
- **Bearing on verbs.** Closest published shape to verbs' claim (structure-preserving edits in C++). **M**. Search-level,
  plus title page.

### Seeding defects

**Just et al., "Are Mutants a Valid Substitute for Real Faults in Software
Testing?" FSE 2014.**
https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf
- **Finding.** On 357 real faults, mutant detection correlates with real-fault detection independently of
  coverage. However, 27% of real faults are *not coupled* to any mutant from standard operators.
- **Bearing on verbs.** Mutants are a partial proxy only. **S**. Read (abstract, §4).

**Petrović et al., "Practical Mutation Testing at Scale: A View from Google,"
2021.** arXiv:2102.11378v2. https://arxiv.org/abs/2102.11378
**Petrović et al., "Does mutation testing improve testing practices?" ICSE 2021.**
arXiv:2103.07189v1. https://arxiv.org/abs/2103.07189
- **Findings.** Mutate changed code incrementally during review, with mutants filtered and capped. At Google scale, mutants are coupled to real
  faults, and developers exposed to mutants write better tests.
- **Bearing on verbs.** The incremental, diff-scoped approach is the right shape for running on the fleet. **S**. Abstract.

**Denisov & Pankevich, "Mull it over: mutation testing based on LLVM," ICSTW
2018.** arXiv:1908.01540v1. https://arxiv.org/abs/1908.01540
- **Method.** Mutation at the IR level (arithmetic, negated conditions, removed void calls, replaced call results,
  scalar replacement), with Clang-AST "junk" filtering. Mutants are less precise at IR level than at source level.
- **Bearing on verbs.** Its operators seed *generic* faults, not the structural faults verbs claims to catch. **M**. Read (§IV).

**Wang et al., "A Comprehensive Study on LLMs for Mutation Testing," TOSEM.**
arXiv:2406.09843v5. https://arxiv.org/abs/2406.09843
- **Finding.** Tested on 851 real Java bugs. LLM-generated mutants detect 76.47% of the real bugs, versus 44.15% for rule-based mutants. They are worse on
  non-compilable (+32.73 points), duplicate and equivalent rates. **S**. Read (abstract).

**Tip, Bell, et al., "LLMorpheus," 2024.** arXiv:2404.09952v2.
https://arxiv.org/abs/2404.09952
- **Finding.** LLM mutants reproduce real bugs exactly in 10 of 40 cases, and reproduce the same failures in 26 more. **M**.
  Search-level.

**Yang et al., "SWE-smith," NeurIPS 2025 D&B.** arXiv:2504.21798v2.
https://arxiv.org/abs/2504.21798
- **Method.** Bug synthesis in real repositories by LM modification, LM rewrite, procedural AST edits, or
  PR inversion. A candidate is kept only if it breaks passing tests. **S** (as an instrument). Read (overview).

**Sonwane et al., "BugPilot," ICLR 2026.** arXiv:2510.19898v2.
https://arxiv.org/abs/2510.19898
- **Method.** Agents implement features and *unintentionally* break tests. These bugs look more like human-authored
  edits than deliberate perturbations, which skew toward short single-file fixes.
- **Bearing on verbs.** This is exactly the case verbs targets: faults an agent introduces itself. **M**. Read (abstract).

**Also acquired; not central to verbs:** Gehring et al., "RLEF," ICML 2025,
arXiv:2410.02089v2 (RL teaches models to use execution feedback across turns).

---

## 6. Synthesis

### Feedback shape

1. **Mechanical, specific feedback is the active ingredient.** Self-critique
   bottlenecks repair (Olausson). Models detect their own C faults poorly, but fix them well
   when given an analyzer report (Dolcetti). Fixable classes are the mechanically
   namable ones, such as syntax, types and compile errors. Logic errors respond much less
   (Zhang & Kothari).
   - So verbs should report concrete, located facts: subject, predicate, the
     transformation that broke it, and where.
   - Hypotheses should not appear in the hot path, consistent with the brief's
     observation/hypothesis split.
2. **Small, ranked, scoped payloads.**
   - SWE-agent filtered flake8 to a handful of codes.
   - openJiuwen ranks, deduplicates and limits per file and in total.
   - Generative compilation's gain comes partly from fewer diagnostics per message.
   - AutoVerus feeds *one* prioritized error per round, with repair guidance specific to its class.

   This supports the brief's terse delta header. It also suggests the
   `suggest:` line should be specific to the error class and point at a vlib
   construct, not be generic.
3. **The message should carry the attempted change and the prior state**, not
   just the error. This is a qualitative SWE-agent finding.
4. **Key deltas on scope, not lines.** Lanser credits deltas only under a stable scope.
   This is design-level agreement with the brief, not measured evidence.
5. **"Diagnostic cleared" is not "fixed".** CORE needed a second-stage judge for unfaithful fixes, and the
   Illusion of Safety study shows static warnings miss runtime violations. verbs output
   should never present a resolved diagnostic as a correctness claim.

### Feedback timing

- **The largest measured effect is having the feedback at all.** In generative compilation, compile errors fall from 65.9% to 20.7%
  with post-hoc feedback.
- **Earlier feedback adds a smaller, real increment.**
  - Generative compilation: 20.7% to 13.1% when checking during generation, at *lower* total runtime.
  - SWE-agent: 15.0% to 18.0% with an edit-time gate.
- **Mechanism.** Catching the first bad edit prevents cascades, and recovery odds fall from 90.5% to 57.2%
  after one failure.
- **No published study varies only diagnostic timing.** No study holds model, tools and tasks fixed and changes only when
  diagnostics run (searched; none found). Our experiment can measure this directly by
  adding a third arm (see below).

### Daemon or on-demand

- **The evidence argues for push.**
  - When checking is a tool the agent may call, it mostly doesn't: 3–22% of
    Kiro conversations, 0–6% LSP use on localization tasks.
  - Optional recoverable context goes unused (Fan et al.).
  - Meanwhile, strong models burn turns on redundant self-initiated verification.

  Feedback must arrive *in the edit tool's result*, as the brief proposes and
  SWE-agent, Fan et al. and openJiuwen all do.
- **Push does not require a resident process.**
  - None of these works measured what residency itself buys.
  - The edit-boundary requirement is that the result lands in the edit's tool output, within
    a latency budget that is small compared with an agent turn. Turn time is dominated by model
    latency: generative compilation reports added runtimes of hundreds of seconds per sample from
    feedback rounds alone.
  - The *delta* needs prior state, but the caller (Blackbird) or a cache file can hold
    that.
- **Recommendation.**
  1. Start with a stateless `verbs check --changed <paths>` that Blackbird's edit hook calls
     on every edit, and that returns the delta against the stored previous result.
  2. Measure cold latency per affected translation unit on blackbird, Oxcart and BRepGPU.
  3. Introduce residency only if the measured latency exceeds the budget. Residency's benefit is
     clangd preamble and index warmth, which is a latency optimization, not a capability.

  This is a measurement question for the toolchain lane, not a literature one.
- **Corollary from the Goodhart evidence.** Push feedback is also *pressure*. ImpossibleBench shows that feedback loops raise
  cheating (33% to 38%) as well as legitimate success. AdaTrans and the practitioner reports show agents
  silencing checkers. The edit-boundary report must therefore treat new suppressions as
  first-class diagnostics. Examples:
  - `NOLINT`;
  - `#pragma clang diagnostic`;
  - `const_cast`, `mutable` or `[[assume]]` additions;
  - weakening a vlib type to a raw integer;
  - edits to `.verbs/` decisions or lint configuration.

### Experiment design for blackbird, Oxcart and BRepGPU

1. **Paired, randomized, pre-registered.**
   - Every task runs in both arms (without verbs, with verbs), with the same model, harness, prompt and budget,
     and R ≥ 5 rollouts per arm.
   - Analyze within task, because difficulty confounds trajectory metrics (Mehtiyev).
   - Fix the task list before randomization (METR). Pre-register hypotheses, metrics, minimum
     effect and sample size.
   - Audit the harness against the ABC checklist for task and outcome validity.
2. **A third timing arm.** Run verbs on demand as a callable tool, versus pushed at the edit boundary. This directly
   answers the daemon/push question and fills the literature gap.
3. **Three defect sources, analyzed separately.**
   - (a) **Structural seeds matching verbs' claims.** For example: kind swaps between same-typed IDs,
     enum domain widening, a new non-const accessor to an invariant field, mutation then
     throw without rollback, moved-from use. Generate them SWE-smith style (scripted AST edits or LLM
     rewrites), keeping only seeds that compile.
   - (b) **Generic Mull mutants as a *control* class.** verbs should not detect these beyond what tests
     already do. A verbs "effect" here signals confounding or noise. Mutants cover only part of
     real faults (27% uncoupled, Just 2014), so they cannot stand alone.
   - (c) **Self-introduced faults.** Give agents feature tasks (BugPilot style) and measure edits from the faulting
     edit to detection. This is verbs' real use case, and the most realistic one.
   - Also mine fixed bugs from each repository's history, reverting the fix to create a task.
   - Tasks from private repositories avoid training-data contamination (the SWE-bench+ leakage problem).
4. **Independent oracles.**
   - For seeded faults, ground truth is known by construction.
   - For final correctness, use developer tests plus held-out tests, plus differential comparison to the known-good revision
     (PatchDiff style), plus ASan/UBSan runs. Static warnings miss runtime violations in C++.
   - Never use verbs' own diagnostics as an outcome oracle.
5. **Define edits-to-detection precisely.** Count file-modifying actions from the faulting edit, or from the
   task start for seeded faults, to the first action that targets the fault site after it is
   reported. Also report:
   - tokens-to-success at iso-accuracy (Xu), tool calls, wall-clock;
   - final correctness;
   - suppressions added;
   - structural regressions (NITR shows tests miss them).
6. **Gaming controls.**
   - Tests, `.verbs/` and lint configuration are read-only during runs (ImpossibleBench).
   - Detect edits to protected paths and new suppression constructs mechanically.
   - Run an LLM judge over trajectories, with human review of a sample (EvilGenie).
   - Include "impossible" variants, where a verbs check conflicts with the specification, to measure
     whether verbs pressure induces cheating.
7. **Model coverage.**
   - Run the current frontier model Blackbird uses plus one weaker model.
     The harness gap shrinks with stronger models (Mehtiyev), so the effect on the frontier model decides
     the kill criterion.
   - Rerun when the model changes. A perceived benefit is not a result (METR RCT).
8. **Kill criterion stated in advance.** For example: on class (a) and class (c), the paired median
   reduction in edits-to-detection has a confidence interval excluding zero. Final correctness does not decrease. The
   suppression rate does not rise. Class (b) shows no spurious effect. Mutant and rollout
   runs go to the fleet, per doctrine.

## 7. Gaps

- No controlled study isolates diagnostic timing (push at edit vs on-demand vs end of task).
- No peer-reviewed measurement exists of agents suppressing static-analysis diagnostics.
- No agent study uses clang-tidy or clang analyses on C++ in the loop; the nearest are Defects4C (functional repair) and NITR
  (structural oracles).

## Acquired PDFs (papers/)

| File | Source |
| --- | --- |
| yang-2024-swe-agent-agent-computer-interfaces-neurips.pdf | arXiv:2405.15793v3 |
| agrawal-2023-monitor-guided-decoding-neurips.pdf | arXiv:2306.10763v2 |
| mundler-2025-type-constrained-code-generation-pldi.pdf | arXiv:2504.09246v2 |
| olausson-2024-self-repair-silver-bullet-iclr.pdf | arXiv:2306.09896v5 |
| gehring-2025-rlef-execution-feedback-icml.pdf | arXiv:2410.02089v2 |
| blyth-2025-static-analysis-as-feedback-loop.pdf | arXiv:2508.14419v1 |
| dolcetti-2024-llm-code-feedback-testing-static-analysis.pdf | arXiv:2412.14841v2 |
| zhang-kothari-2026-iterative-feedback-loops-code-correction.pdf | arXiv:2606.17514v1 |
| zhang-2025-rl-compiler-language-server-feedback-lanser.pdf | arXiv:2510.22907v2 |
| xu-2026-language-server-tokens-coding-agents.pdf | arXiv:2608.13568v1 |
| openjiuwen-2026-beyond-static-harnesses-coding-agents.pdf | arXiv:2608.27969v1 |
| fan-2026-harness-design-coding-agents.pdf | arXiv:2609.20804v1 |
| mundler-sasahara-2026-generative-compilation.pdf | arXiv:2607.13921v2 |
| zhong-2025-impossiblebench-iclr.pdf | arXiv:2510.20270v1 |
| gabor-2025-evilgenie-reward-hacking-benchmark.pdf | arXiv:2511.21654v2 |
| baker-2025-monitoring-reasoning-models-obfuscation.pdf | arXiv:2503.11926v1 |
| macdiarmid-2025-emergent-misalignment-reward-hacking-production-rl.pdf | arXiv:2511.18397v1 |
| zan-2025-multi-swe-bench-neurips.pdf | arXiv:2504.02605v1 |
| wang-2025-defects4c-cpp-repair-ase.pdf | arXiv:2510.11059v2 |
| zhu-2026-nitr-needle-in-the-repo-cpp-maintainability.pdf | arXiv:2603.27745v1 |
| wang-2026-swe-bench-solved-issues-patchdiff-icse.pdf | arXiv:2503.15223v2 |
| yu-2025-utboost-swe-bench.pdf | arXiv:2506.09289v1 |
| aleithan-2024-swe-bench-plus.pdf | arXiv:2410.06992v2 |
| zhu-2025-agentic-benchmark-checklist-neurips.pdf | arXiv:2507.02825v5 |
| yang-2025-swe-smith-neurips.pdf | arXiv:2504.21798v2 |
| sonwane-2025-bugpilot-iclr.pdf | arXiv:2510.19898v2 |
| wang-2026-llm-mutation-testing-study.pdf | arXiv:2406.09843v5 |
| tip-2024-llmorpheus-mutation-testing.pdf | arXiv:2404.09952v2 |
| denisov-2018-mull-llvm-mutation-testing-icstw.pdf | arXiv:1908.01540v1 |
| majgaonkar-2025-code-agent-trajectories.pdf | arXiv:2511.00197v1 |
| mehtiyev-2026-behavioral-drivers-coding-agents.pdf | arXiv:2604.02547v1 |
| yang-2025-autoverus-oopsla.pdf | arXiv:2409.13082v3 |
| aggarwal-2025-alphaverus-icml.pdf | arXiv:2412.06176v1 |
| wadhwa-2024-core-code-quality-llms-fse.pdf | arXiv:2309.12938v1 |
| svoboda-2025-c-cpp-static-analysis-alert-repair.pdf | arXiv:2508.02820v1 |
| mahmud-2026-illusion-of-safety-cpp-verification.pdf | arXiv:2607.00107v3 |
| liu-2026-adatrans-c-to-rust.pdf | arXiv:2606.31706v1 |
| becker-2025-metr-developer-productivity-rct.pdf | arXiv:2507.09089v2 |
| jarmak-2026-engineering-reliable-coding-agents.pdf | arXiv:2608.13867v1 |
| deligiannis-2023-rustassistant-fixing-rust-compilation-errors.pdf | arXiv:2308.05177v1 |
| petrovic-2021-google-mutation-testing-practices-icse.pdf | arXiv:2103.07189v1 |
| petrovic-2021-practical-mutation-testing-at-scale-google.pdf | arXiv:2102.11378v2 |
| just-2014-mutants-valid-substitute-real-faults-fse.pdf | homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf |
| rogero-2026-miri-state-of-reward-hacking.pdf | intelligence.org (Sept 2026 report) |

Web-only sources (no PDF): Kiro diagnostics blog, METR reward-hacking post,
practitioner lint-suppression issues (URLs above).
