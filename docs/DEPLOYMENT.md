# Commercial Deployment Architecture

DDC Action Lifecycle should support three production deployment models while preserving the same evidence semantics.

## 1. Managed DDCAL

Best for pilots and smaller teams.

Data path:
customer adapter -> authenticated ingestion -> lifecycle runtime -> evidence store -> review/export API

Requirements before production:
- tenant-scoped identities and authorization;
- tenant-isolated storage and encryption keys where practical;
- encrypted transport and storage;
- no training use of customer evidence;
- configurable retention/deletion;
- immutable/auditable administrative actions;
- export of complete customer evidence bundles;
- rate/resource limits;
- backup and tested recovery;
- security event logging;
- incident-response process.

## 2. Customer VPC

Best for enterprise customers who want managed software without evidence leaving their cloud boundary.

Altru.dev supplies:
- deployment package;
- versioned runtime;
- conformance tests;
- upgrade tooling;
- support.

Customer controls:
- cloud account;
- storage;
- identity provider;
- network boundary;
- keys/secrets;
- retention.

## 3. Self-hosted / air-gapped

Best for high-assurance or restricted environments.

The runtime should work without mandatory outbound telemetry or remote code execution.

Licensing can use an offline entitlement file or customer-specific signed license artifact rather than requiring continuous external connectivity.

## Evidence storage model

Separate:
- immutable lifecycle events;
- external evidence blobs;
- indexes/search metadata;
- checkpoints/signatures;
- generated review reports.

An event should normally contain a digest/reference rather than large or sensitive raw evidence.

This keeps the immutable action history portable while allowing customer-specific retention policies for raw evidence.

## Production signing

The local checkpoint implemented in v0.1 commits to the complete event set but does not establish external trust.

Production should add pluggable signing:

checkpoint -> canonical bytes -> SHA-256 -> customer/Altru signing boundary

Preferred properties:
- Ed25519 or an enterprise KMS/HSM-backed signing service;
- key identifiers and rotation;
- signed timestamp where appropriate;
- verifier usable without the hosted service;
- optional transparency anchoring for high-assurance deployments.

Signing must remain distinct from evidence truth. A valid signature proves who committed to the bytes, not that the underlying claim is true.

## API boundary

Do not expose the proprietary assurance implementation as downloadable logic in the hosted product.

Public clients should interact through narrow contracts:
- create lifecycle/case;
- append signed/hashed evidence event;
- request decision assessment;
- request next-transition admissibility;
- attach Action Receipt;
- attach Replay reconstruction;
- export evidence bundle;
- verify exported bundle.

Production API work begins only after the v0.1 DSR release gate passes.

## Privacy principle

Store the minimum evidence required for the claim.

Where possible:
- hash/reference sensitive artifacts;
- let the customer retain raw evidence;
- ingest only scoped metadata and commitments;
- make retention explicit;
- avoid telemetry unrelated to assurance.

## Failure behavior

If the runtime cannot establish required evidence state, the production system must not silently degrade ALLOW into "best effort."

Allowed outcomes remain:
ALLOW / BLOCK / RECHECK / REQUIRE_HUMAN / SIMULATE_FIRST / UNKNOWN.
