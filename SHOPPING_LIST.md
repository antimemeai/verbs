# Shopping list

Sources the research lanes could not acquire. Drop acquired PDFs into papers/
and remove the line.

## Literature

- Strom & Yemini, "Typestate: A Programming Language Concept for Enhancing
  Software Reliability", IEEE TSE 12(1):157-171, 1986.
  doi:10.1109/TSE.1986.6312929 (paywalled).
- Garcia, Tanter, Wolff & Aldrich, "Foundations of Typestate-Oriented
  Programming", TOPLAS 36(4):12, 2014. doi:10.1145/2629609 (download reset; a
  CMU KiltHub copy exists).
- Abrahams, "Exception-Safety in Generic Components", LNCS 1766, 2000.
  doi:10.1007/3-540-39953-4_6 (Boost HTML copy was read; PDF missing).
- Cohen, Moskal, Schulte & Tobies, "Local Verification of Global Invariants in
  Concurrent Programs", CAV 2010. doi:10.1007/978-3-642-14295-6_42 (only the
  companion tech report was acquired).
- Hangal & Lam, "Automatic Dimension Inference and Checking for Object-Oriented
  Programs" (UniFi), ICSE 2009. Linked from suif.stanford.edu/unifi/.
- O'Callahan, PhD thesis (Ajax), CMU 2001, CMU-CS-01-124.
- Meyer, Object-Oriented Software Construction, 2nd ed. (book).
- Hong & Ryu, "Don't Write, but Return: Replacing Output Parameters with
  Algebraic Data Types in C-to-Rust Translation", PLDI 2024.
  doi:10.1145/3656406 (ACM 403 to curl; open access in a browser).
- Santos et al., "Lifting the curse of stringly-typed code", PeerJ Preprints
  5:e2723v1, 2017 (403).
- Tsantalis & Chatzigeorgiou, "Identification of refactoring opportunities
  introducing polymorphism", JSS 83(3), 2010 (host unreachable).
- Khatchadourian, Sawin & Rountev, "Automated Refactoring of Legacy Java
  Software to Enumerated Types", ASE journal 2017. doi:10.1007/s10515-016-0208-8.
- Mastrangelo, Hauswirth & Nystrom, "Casting about in the Dark", OOPSLA 2019.
  doi:10.1145/3360584 (abstract only).
- WG21 P1371R3 (inspect) and P2211R0 (exhaustiveness checking for C++
  pattern matching).
- Bierhoff & Aldrich, "Modular Typestate Checking of Aliased Objects",
  OOPSLA 2007 (Plural).
- Whaley, Martin & Lam, "Automatic Extraction of Object-Oriented Component
  Interfaces", ISSTA 2002.
- Said, Quante & Koschke, "Mining understandable state machine models from
  embedded code", EMSE 2020.
- Jespersen, Munksgaard & Larsen, "Session Types for Rust", WGP 2015.
- Duarte & Ravara, "Taming stateful computations in Rust with typestates",
  J. Computer Languages 2022.
- Kellogg et al., "Verifying Object Construction", ICSE 2020, and the
  resource-leak checker extended version, STTT 2025.
- Sakkas, Sahu, Ong & Jhala, "Neurosymbolic Modular Refinement Type
  Inference", ICSE 2025.
- Szalay, Sinkovics & Porkoláb, "Practical heuristics to improve precision
  for erroneous function argument swapping detection in C and C++", JSS 181
  (2021) 111048.
- Liargkovas, Panourgia & Spinellis, "Quieting the Static",
  arXiv:2311.07482.
- SafeTrans (arXiv:2505.10708), SACTOR (arXiv:2503.12511), RobustAPI
  (arXiv:2308.10335), arXiv:2605.22534, arXiv:2606.13468: full texts.

## Reference implementations

- Lackwit source (O'Callahan & Jackson 1997). Not on GitHub; check the
  authors' pages.
- clazy (https://invent.kde.org/sdk/clazy): how a library ecosystem's Clang
  plugin handles ABI pinning and suppression comments; only the README read.
- ui_test (https://github.com/oli-obk/ui_test), the harness clippy uses.
- Optional: deranged, Kestrer/bounded-integer, nutype, davidstone/operators,
  Chromium base/numerics, Wuffs; the bounded lane read them from source but
  did not keep copies.
