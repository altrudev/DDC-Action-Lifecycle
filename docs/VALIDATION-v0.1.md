# v0.1 Validation Plan

DDC Action Lifecycle must not be described as release-PASS until the exact candidate revision has been validated in a governed DSR environment.

## Required execution

Bind the job to the exact Git commit SHA and use an isolated worktree or clean checkout.

The validation run must:

1. build/install the package in a clean Python 3.10+ environment;
2. run the complete pytest suite;
3. execute `examples/basic_lifecycle.py`;
4. execute `examples/retry_delayed_confirmation.py`;
5. validate `conformance/valid-profiled-allow-v0.1.jsonl` with the CLI;
6. assess its `decision-1` decision with the CLI;
7. verify the expected result is VALID / ALLOW;
8. exercise package build metadata and console-script installation;
9. record stdout, stderr, exit codes, interpreter/platform versions, exact revision, and dependency versions.

## Required negative evidence

The evidence bundle must show that tests cover at least:

- event mutation;
- nested payload mutation;
- unknown/duplicate parent references;
- retroactive evidence;
- later backfilled evidence;
- actor-specific evidence horizons;
- unusable/stale evidence;
- healthy/degraded/unreachable/unknown evidence-channel states;
- actor-specific historical channel visibility;
- required-but-missing channel assurance;
- channel delivery-latency policy violations;
- required-but-unconsulted evidence;
- unresolved contradictions/assumptions on ALLOW;
- source-independence shortfall;
- post-action evidence contamination;
- typed evidence relationships without chronology-to-causality promotion;
- deterministic evidence bundles across equivalent independent ingestion orders;
- invalid artifact digests;
- duplicate JSON keys;
- NaN/non-finite JSON;
- event-count, parent-fan-in, byte-size, and nesting bounds;
- checkpoint omission/tampering;
- branch preservation;
- Action Receipt / Agent Replay bridge separation.

## Evidence bundle

A valid DSR result should include:

- repository and exact commit SHA;
- job/request identifier;
- worker identity;
- request/admission/execution/result timestamps;
- command manifest;
- test totals and failures;
- SHA-256 of significant output artifacts;
- signed/hashed DSR result where supported;
- explicit unresolved limitations.

## Independent examiner

After deterministic tests pass, an independent examiner should review the bundle against the DDC Radial invariants in `docs/RADIAL-REVIEW-v0.1.md`.

The examiner must not upgrade a deterministic test PASS into claims the tests do not establish. In particular, local correctness does not establish trusted external identity, source honesty, legal authority, or real-world consequence.

## Release gate

Only after the governed run and examiner pass should the branch be considered for merge and v0.1 release labeling.
