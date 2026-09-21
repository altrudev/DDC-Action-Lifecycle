# Frozen retry / reconciliation case — v0.1

Status: local conformance design. It is not an OpsWatch result and does not predict Jason McGill's independent determination.

This case exists to test the boundary that motivated the latest DDC Action Lifecycle invariants.

## Incident

1. Attempt A crosses an execution boundary.
2. Its downstream consequence cannot initially be established.
3. The actor receives a bounded evidence view through a named evidence channel.
4. At the retry decision time, later provider truth is not yet in that actor's historical horizon.
5. Attempt B is performed as a retry or reconciliation.
6. Attempt B changes downstream state and causes new evidence records to exist.
7. Later reconstruction may use those records, but must identify their lineage and must not treat them as neutral contemporaneous evidence of Attempt A.
8. The reconstruction preserves anything neither evidence set can establish.

## Required determinations

A conforming implementation must keep these questions separate:

- what happened to Attempt A;
- what the actor could know at retry-decision time;
- whether the retry decision was justified from that historical evidence state;
- whether the evidence channel was adequate for the decision policy;
- which later evidence genuinely supports claims about Attempt A;
- which evidence was created or contaminated by Attempt B or reconciliation;
- what remains unproven.

## Required invariants

- later truth != retroactive knowledge;
- decision failure != evidence-channel failure;
- execution crossing != downstream consequence;
- evidence existence != actor accessibility;
- actor accessibility != freshness;
- chronology != causality;
- evidence lineage is explicit;
- retry-created evidence cannot silently become neutral evidence of the original attempt;
- reconstruction appends; it does not mutate earlier evidence states;
- disagreement between independent reconstructions is preserved rather than forced into one answer.

## Blind comparison protocol

When an external independent reconstruction is performed, both parties receive the same frozen source record. Neither party sees the other's determination until both outputs are frozen. Comparison focuses on evidence boundaries, disagreement points, and unresolved claims rather than requiring matching verdicts.
