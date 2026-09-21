# DDC Action Lifecycle — Commercial Product Definition

## Product promise

**Before. During. After. One evidence-bound action history.**

DDC Action Lifecycle is commercial assurance infrastructure for consequential software-agent actions. It is designed to answer four operational questions without merging them into one unsupported claim:

1. What was the actor authorized to do?
2. What evidence was available and actually used when the decision was made?
3. What exact action was dispatched/executed?
4. What can admissible evidence establish happened afterward?

The commercial product is not a logging dashboard. Its differentiator is preserving the boundary between historical knowledge and later reconstruction, then using current evidence to determine whether the next transition remains admissible.

## Product family

### 1. DDC Action Lifecycle Runtime

The core commercial engine.

Customers integrate their agent, orchestration, payment, cloud, MCP, robotics, or workflow system with the runtime. It maintains the append-only action evidence graph and evaluates evidence-bound next transitions.

Primary buyers:
- AI/agent platform engineering;
- security architecture;
- payments/fraud/risk;
- enterprise automation;
- cloud/platform reliability;
- regulated or safety-sensitive automation.

Deployment:
- self-hosted;
- private VPC;
- managed DDCAL service.

Commercial unit:
- consequential actions / lifecycle cases processed;
- enterprise annual license for self-hosted/private deployment.

### 2. DDC Evidence Review

A review and investigation product built on the same evidence model.

Input:
- lifecycle exports;
- Action Receipts;
- Agent Replay reports;
- logs/telemetry converted into lifecycle evidence.

Output:
- evidence bundle;
- historical decision assessment;
- consequence reconstruction status;
- contradictions / unknowns;
- boundary where proof stops;
- signed/hashed review artifact where deployment supports it.

Primary buyers:
- security/incident response;
- audit;
- AI assurance teams;
- insurers / risk teams;
- external assessors.

Commercial unit:
- per case / review;
- team subscription;
- enterprise evidence-review workspace.

### 3. DDC Action Gateway

A narrow enforcement surface placed immediately before consequential tools.

It consumes lifecycle evidence and emits:
- ALLOW;
- BLOCK;
- RECHECK;
- REQUIRE_HUMAN;
- SIMULATE_FIRST;
- UNKNOWN.

It does not replace IAM. Identity and permission systems establish who/what may access a tool. Action Gateway evaluates whether this exact transition remains evidence-supported now.

Primary integrations:
- MCP tools;
- payment execution;
- cloud/admin operations;
- CI/CD;
- database/admin actions;
- physical/robotic control gateways.

Commercial unit:
- guarded actions;
- gateway instance;
- enterprise site license.

## Shared evidence bundle

Every paid product should be able to produce a portable DDC Evidence Bundle containing:

- lifecycle identity;
- exact event digests;
- lifecycle checkpoint;
- decision assessments;
- next-transition dispositions;
- branch/retry map;
- latest reconstruction;
- explicit limitations;
- deterministic bundle digest.

This is the product's portable evidence artifact. A customer should be able to export it even if they stop using the hosted service.

## What remains open

The public interoperability language stays open so external systems can produce compatible evidence:

- schemas;
- public specification;
- examples;
- conformance vectors.

The commercial value stays in:
- runtime evaluation;
- DDC Radial assurance logic;
- enforcement;
- orchestration;
- managed evidence services;
- enterprise integrations;
- operational tooling;
- review console;
- deployment/support.

See `LICENSE-POLICY.md`.

## Product principle

**Open the evidence language. Protect the assurance engine.**

Interoperability should reduce customer lock-in without giving away the commercial runtime.
