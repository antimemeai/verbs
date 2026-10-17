# Jev coverage audit: are the first tribunal's findings addressed by SPEC revision 2?

2026-10-17. Script and raw answers: context/jev-audit/ (audit.py,
results.jsonl).

## Method

There was one Jev request per finding, 92 in all: every `### ID.` section of
the four tribunal reports and the soundness report's bulleted minors.
- **Model:** `jev-1.13.0`.
- **State:**
  - `spec`: the whole of design/SPEC.md at commit 1f03e75;
  - `finding`: the finding's text, truncated to 3,000 characters;
  - a note that the finding's section numbers refer to revision 1.
- **Question:** one Choice. Its options were:
  - `resolved`;
  - `resolved_by_removal`;
  - `deferred` (a named bead, or outside the §2.1 boundary);
  - `partial`;
  - `unaddressed`;
  - `pending_section5` (enum candidates, still a placeholder).
- **Cost:** 1,162,861 input tokens, about $0.05.

Jev's answer is a filter, not the verdict. Every finding where
resolved + removed + deferred had probability below 0.75 was re-read against
the spec by hand.

## Jev's distribution

| Choice | n |
|---|---|
| resolved | 59 |
| resolved_by_removal | 14 |
| partial | 11 |
| pending_section5 | 6 |
| deferred | 1 |
| unaddressed | 1 |

## Adjudication of the flagged findings

| Finding | Jev | Reading | Action |
|---|---|---|---|
| checks B3 | partial 0.54 | Resolved. Each of its seven bypasses maps to a spec rule: Refined dropped; list-init is §4.2 rule 7; `void*` is rule 1; explicit instantiation is rule 10; specializations are rule 9; keyword macros are rule 11; UB is boundary rule 8. | none |
| checks M2 | partial 0.72 | Resolved by §4.6 and §4.7: no suppression comment is honoured; every pragma spelling, system_header, the argv diff and assumptions are covered; lost claims print `!`. | none |
| checks M7 | resolved 0.56 | Resolved. §6.2 covers all nine sub-cases: negative probes, database diff, traces, files not in the database, dropped entries, PCH, modules `outside`, `#embed`, and platform-guarded code under rule 7. | none |
| checks M8 | resolved 0.52 | Resolved. §6.4 keys, and the `~` prefix for changed evidence. Parameter keys are moot because parameters are not subjects. | none |
| checks M11 | partial 0.76 | **Partly open.** The budget, cost model, over-budget behaviour and gate are in §6.6. Missing: the full-scan cost of a first run, and job slots shared across concurrent processes. | §6.6 states both; bead verbs-de3.34 |
| doctrine D23 | partial 0.50 | Resolved. §3.1 throws `verbs::violation`, terminates inside `noexcept`, and allows no handler. | none |
| doctrine D25 | partial 0.50 | **Open.** The spec did not give the exit status for compile errors, nor the treatment of a unit that never compiles. | §6.2: compile errors never change the exit; never-compiled units are `outside`, printed once |
| soundness m3 | resolved 0.41 | **Open, and a false `holds`.** `&D` passed to a function that no analyzed unit defines left D `holds`; rule 7 assumed this case rather than checking it. | §4.4 "Unanalyzed definitions": such types are `outside`, named |
| ergonomics M2 | partial 0.70 | Resolved by `= delete("…")`, named bound constants, and `-verify`. | none |
| ergonomics m4 | partial 0.51 | Mostly resolved. The narrowing message's text was unstated. | §3.3: one generic message naming both spellings |
| ergonomics m1 | partial 0.49 | Resolved. §3.3 "Mixed ranges" names the idiom. | none |
| ergonomics m6 | unaddressed 0.59 | Resolved. The finding asks for no change beyond free-template operators, which §3.3 has. | none |
| doctrine D12 | partial 0.53 | Resolved as deferral. `Bounded` lands only when a blackbird declaration is named; otherwise it becomes a bead. Refined and Id are beads. | none |
| doctrine D22 | partial 0.47 | Split. "verbs-domain enum" is defined in §3.2. "Literal" and "outside the analyzed code" are §5 terms, waiting on the lane. | §5 lane |
| checks B2, M4, M5, M6, m6; doctrine D4; ergonomics M8 | pending | §5 enum candidates. | §5 lane |

## What Jev did well and badly here

It correctly placed every enum-candidate finding as pending §5. Its
`partial` answers clustered on findings with many sub-items (checks B3, M2,
M7), where every item is addressed but in different sections. This is the
vendor's documented weakness with indirection. It found two of the three real
gaps (D25 and M11, both `partial`). It ranked the third, soundness m3, as
`resolved`, at the lowest confidence of any `resolved` answer (0.29). The low
confidence, not the label, is what surfaced it.

For future audits: the useful signal was the probability mass off `resolved`,
not the selected key. Per-sub-item questions would cut the many-part false
alarms.

## Round 2: first-round external findings against revision 3

Script and answers: context/jev-audit/audit2.py and results2.jsonl. There
were 35 findings: ChatGPT F01–F21 and MiMo F1–F14, with the same question
and options (no `pending_section5`). Jev's answers:

| Choice | n |
|---|---|
| resolved | 27 |
| resolved_by_removal | 2 |
| deferred | 1 |
| partial | 5 |

Re-read by hand: every finding where resolved + removed + deferred had
probability below 0.75 (14). Four of the `partial` answers were multi-part
findings closed across sections, as in round 1: ChatGPT F14, and MiMo F2,
F3 and F10. Two answers exposed real loose ends:
- **ChatGPT F08** (0.38). "Never compiled → outside" was ambiguous for a new
  unit still being written. Now the path rule lists units the pinned Clang
  cannot compile, and every other failing unit suspends the report.
- **MiMo F8** (0.15). The experiment did not say how a run with no faulty
  edit scores. It now scores 0, and the oracle confirms the fault is absent.

The other eight are confirmed resolved on reading.
