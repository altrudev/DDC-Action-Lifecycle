# DDC Action Lifecycle

**Before. During. After. One evidence-bound action history.**

DDC Action Lifecycle connects decision-time assurance, signed action commitments, execution evidence, downstream observations, and later reconstruction without allowing hindsight to rewrite what was knowable earlier.

> A later phase may reference an earlier evidence state, but it may never mutate it.

## What it is

DDC Action Lifecycle is the integration layer between:

- **DDC Action Receipt** — the immutable decision/execution commitment;
- **Agent Replay** — the reconstruction engine;
- **DDC Physical Gate** — next-transition enforcement;
- **BoundaryProof** — evidentiary-boundary verification.

It does not collapse those components into one trust claim. It connects them through an append-only evidence graph.

```text
Intent
  ↓
Authority
  ↓
Evidence State
  ↓
Decision
  ↓
Action Receipt
  ↓
Dispatch
  ↓
Execution
  ↓
Observation
  ↓
Consequence
  ↓
Replay / Reconstruction
  ↓
Next-transition admissibility
```

## Why

A later record may prove that something happened at 10:01 even though the deciding agent did not receive that evidence until 10:08.

If the agent made a retry decision at 10:05, the 10:08 evidence can improve the later reconstruction but cannot be inserted into the agent's historical knowledge state.

The lifecycle therefore preserves two separate questions:

1. **What can we establish happened now?**
2. **What was the actor justified in concluding then?**

## Current v0.1 foundation

The reference runtime currently provides:

- immutable lifecycle events with canonical SHA-256 commitments;
- explicit causal parent edges rather than inferred causality;
- actor-specific historical evidence horizons;
- event time, record time, evidence creation time, and availability time;
- evidence usability facets: existence, reachability, discoverability, freshness, accessibility, trust;
- required-versus-consulted evidence checking;
- explicit UNKNOWN / UNPROVEN states;
- contradiction and unresolved-assumption preservation;
- retry/alternate-route branch preservation;
- Action Receipt and Agent Replay artifact bridges;
- next-transition dispositions: ALLOW, BLOCK, RECHECK, REQUIRE_HUMAN, SIMULATE_FIRST, UNKNOWN;
- verified JSONL import/export;
- bounded event size, event count, and parent fan-in;
- deterministic UTF-8 canonical serialization with UTF-16 object-key ordering and no floating-point values;
- a CLI for validation, summaries, and historical decision assessment.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q

python examples/retry_delayed_confirmation.py
```

Validate an exported lifecycle:

```bash
ddc-lifecycle validate lifecycle.jsonl
ddc-lifecycle summary lifecycle.jsonl
ddc-lifecycle assess-decision lifecycle.jsonl decision-1
ddc-lifecycle bundle lifecycle.jsonl
```

## Public interoperability

The public event contract lives under:

- `schemas/`
- `docs/spec/`
- `examples/`

Those materials are intended to let other systems emit, consume, and test compatible evidence without receiving the proprietary DDC runtime.

See `LICENSE-POLICY.md`.

## Assurance boundary

A lifecycle digest proves integrity of the committed event bytes. It does **not** by itself prove actor identity, authority, source honesty, trusted time, policy correctness, or downstream physical/economic consequence.

Each of those claims must earn its own evidence.

See `SECURITY.md`, `docs/ARCHITECTURE.md`, and `docs/RADIAL-REVIEW-v0.1.md`.

## Commercial product path

The repository now defines three commercial surfaces:

- **DDC Action Lifecycle Runtime** — continuous evidence-bound action assurance;
- **DDC Evidence Review** — incident/review product producing portable evidence bundles;
- **DDC Action Gateway** — enforcement immediately before consequential tool execution.

See `docs/PRODUCT.md`, `docs/COMMERCIALIZATION.md`, `docs/DEPLOYMENT.md`, and `docs/PILOT.md`.

The runtime can export a deterministic evidence bundle containing the lifecycle checkpoint, decision assessments, next-transition dispositions, branches, latest reconstruction, limitations, and a bundle digest.

## Status

**v0.1 foundation — implementation in progress.**

The repository must not be described as DSR-validated or release-PASS until the exact revision has been executed in a governed environment and a signed/hashed evidence bundle has been independently examined.

## Attribution

DDC Action Lifecycle and the broader DDC architecture are designed and developed by **Valentyn Rukhaylo / Altru.dev**.

Several evidence/replay invariants were materially sharpened through Valentyn Rukhaylo's public technical engagement with **Jason McGill**, particularly around downstream consequence boundaries, contemporaneous versus later evidence, the three-clock model, actor-specific evidence horizons, and consequence-versus-decision reconstruction.

DDC Radial analysis extended those refinements into required-versus-consulted evidence, evidence-channel adequacy, causal evidence provenance, post-action contamination, branch preservation, and continuous evidence-bound execution.
