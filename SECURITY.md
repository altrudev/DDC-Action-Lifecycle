# Security Policy

DDC Action Lifecycle is an early reference implementation. It is not a safety certification, authorization service, identity provider, trusted timestamp service, or proof of physical/economic outcome.

## Security properties in scope

The reference runtime is designed to:

- preserve append-only lifecycle history;
- detect event-content mutation through canonical digests;
- reject unknown parents and duplicate event identifiers;
- prevent historical evidence from leaking backward across an actor's decision horizon;
- preserve retry branches and uncertainty;
- fail a profiled ALLOW when required/consulted evidence invariants are violated;
- bound basic parser/ledger resource use.

## Properties not established by an event digest

A valid event digest does not prove:

- actor identity;
- authority or legal permission;
- source honesty;
- trusted wall-clock time;
- independence of two evidence sources;
- that an external system performed the claimed action;
- that a physical or economic consequence occurred;
- that a policy was correct.

Those claims require separate trust anchors and evidence.

## Threats explicitly considered

- post-hoc mutation of earlier evidence;
- retroactive knowledge;
- chronology-to-causality promotion;
- branch collapse during retries/recovery;
- stale or inaccessible evidence treated as usable;
- inference promoted to observation;
- downstream consequence inferred from dispatch;
- representation divergence in hashed content;
- oversized histories or parent fan-in;
- malicious or mistaken caller-supplied metadata.

## Reporting

Please report suspected security issues privately to the project owner rather than publishing exploit details before coordination.

Do not include credentials, production secrets, patient information, financial account data, or other sensitive customer material in public issues.
