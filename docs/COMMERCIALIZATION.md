# Commercialization Plan

## Beachhead problem

Do not lead with "AI governance."

Lead with a concrete operational failure:

> An autonomous agent performs a consequential action, does not receive complete confirmation, and must decide what to do next. Later evidence changes what we know happened. Can the organization prove what the agent was justified in knowing at the time and prevent the next unsafe transition?

The first commercial demos should use:
1. agentic payment retry;
2. MCP/tool execution;
3. cloud or production change.

If the same evidence runtime works across all three, the market sees infrastructure rather than a single-use feature.

## Buyer message

**Know why an action was allowed, what actually happened, and whether the next action should still proceed.**

Avoid promising "proof of everything." A stronger market claim is:

**DDC shows where proof stops.**

## Initial customer path

### Design partner
One real workflow, synthetic/private-safe data acceptable at first.

Goal:
- map the customer's action boundaries;
- ingest/emit lifecycle evidence;
- demonstrate one decision-time reconstruction;
- demonstrate one post-action reconstruction;
- demonstrate one next-transition gate.

Commercial structure:
- low-cost or no-cost limited pilot only when the customer contributes meaningful workflow access/evidence;
- fixed scope and fixed duration;
- customer keeps its data;
- Altru.dev retains DDC/runtime IP.

### Paid pilot
Deliver:
- integration adapter;
- lifecycle runtime;
- evidence export;
- review report;
- measurable findings;
- security boundary documentation.

Price hypothesis, to validate with customers rather than publish as final pricing:
- small technical pilot: CAD 5k–15k;
- enterprise pilot: CAD 20k–50k+ depending on integration/risk;
- convert successful pilots into annual runtime/support contracts.

### Production
Offer three deployment modes:
- managed DDCAL;
- customer VPC;
- self-hosted enterprise.

Production pricing should be based on economic value/risk and deployment scope, not only compute cost.

Possible models:
- annual platform fee + action volume;
- per guarded consequential action;
- per environment/gateway;
- enterprise site license;
- evidence-review subscription / case pack.

## Minimum commercial readiness gate

Before taking production money, complete:

- governed DSR validation of the exact release;
- external technical review;
- stable public interoperability version;
- versioning/deprecation policy;
- cryptographic signing/verification boundary for production evidence;
- tenant isolation for hosted deployment;
- authentication/authorization for API/service surface;
- retention/deletion controls;
- backup/recovery;
- privacy/data-processing terms;
- commercial license/EULA;
- support/security reporting process;
- pilot contract template;
- basic liability/insurance review appropriate to the target sector.

## Metrics that matter

Do not optimize for repository stars.

Track:
- consequential actions observed;
- decisions with complete required evidence;
- prevented unsafe/unsupported transitions;
- retroactive-knowledge errors detected;
- retry/duplicate-action risks detected;
- evidence gaps surfaced;
- time to reconstruct an incident;
- integration time;
- percentage of lifecycle events independently verifiable;
- pilot-to-production conversion.

## Go-to-market sequence

1. Finish v0.1 deterministic + DSR evidence.
2. Produce a one-click synthetic payment-retry demo and evidence bundle.
3. Recruit 2–3 design partners in different action domains.
4. Use partner feedback to stabilize v0.2 API and adapters.
5. Publish conformance spec and independent validation evidence.
6. Sell paid pilots.
7. Package managed/VPC/self-hosted production offerings.
8. Pursue B.C./Canadian commercialization funding using real pilot evidence.

## Positioning against adjacent categories

IAM answers: who/what may access this tool?

Observability answers: what telemetry was emitted?

Policy engines answer: what rule evaluated true?

Agent Replay answers: what can we reconstruct afterward?

DDC Action Lifecycle connects those boundaries while preserving historical evidence state and controlling the next consequential transition.

That is the commercial category to own: **action evidence infrastructure for autonomous systems.**
