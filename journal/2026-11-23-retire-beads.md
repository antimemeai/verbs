# 2026-11-23: retire beads

The operator is phasing beads out of all work: Dolt's model does not fit
many local projects that move fast. Blackbird retired its tracker on
2026-11-21 (blackbird/AGENTS.md, JOURNAL.md); verbs follows.

**Why now.** On resumption every `bd` command failed with
`database "verbs" not found`. A Dolt server had started at 03:31 against a
fresh, empty `.beads/dolt`. The tracked `.beads/backup/` (2026-10-18
21:09Z, 40 issues, matching HEAD) was the only copy of the issues.

**What was done.**
- Stopped the verbs Dolt server (port 13309).
- Archived the whole `.beads/` directory to
  `~/archives/verbs-beads-2026-11-23.tar.gz`. The backup JSONL also stays in
  git history at ccdefe1.
- Unset `core.hooksPath=.beads/hooks` and `beads.role` in the local git
  config. Git hooks now come from `.git/hooks`, which has none.
- Removed `.beads/`, the Dolt lines in `.gitignore`, and the beads block in
  AGENTS.md.
- Wrote WORK.md from the backup. It holds every open issue's full text: 3
  active (verbs-2or, verbs-g5w, verbs-b4x) and 35 deferred (verbs-4ox,
  verbs-de3.1–35 except the closed .30). Priority, type, labels and the two
  blocking edges are kept on each entry. The umbrella verbs-de3 became the
  section's preamble.
- SPEC, README and the quarantine manifest now point at WORK.md. The old
  names stay as labels so citations in SPEC, journal/ and papers/ resolve.
  Historical journal and papers text is unchanged.

**Not changed.** ~/AGENTS.md still documents bd for every project, and the
workspace BLACKBIRD.md says nothing about tracking. Both are outside this
repository.
