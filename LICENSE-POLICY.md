# DDC Action Lifecycle Licensing Policy

Copyright (c) 2026 Valentyn Rukhaylo / Altru.dev. All rights reserved except where an express file or directory license below grants additional rights.

DDC Action Lifecycle uses a split licensing model so organizations can implement and test the public interoperability language without receiving a license to the commercial assurance engine.

## Apache-2.0 public interoperability materials

The following directories are licensed under the Apache License, Version 2.0:

- `schemas/`
- `examples/`
- `docs/spec/`
- `conformance/` when present

Use, modification, and redistribution of those materials are subject to `LICENSES/Apache-2.0.txt`.

## Proprietary implementation materials

Unless separately licensed in writing, the following are proprietary and are not licensed for reproduction, redistribution, creation of derivative commercial implementations, or commercial hosting:

- `src/`
- runtime and orchestration logic
- DDC Radial logic and internal assurance methods
- enforcement and admissibility logic
- proprietary adapters or service integrations
- private test/evaluation assets when present

Public visibility of source code is not a grant of an open-source license.

## Documentation

`docs/ARCHITECTURE.md`, the README, product descriptions, diagrams, and other documentation outside `docs/spec/` are provided for evaluation and interoperability understanding. They are not licensed as implementation code unless expressly stated.

## Trademarks and names

No license is granted to use DDC, DDC Radial, DDC Action Lifecycle, DDCAL, Altru.dev, Agent Replay, BoundaryProof, or related names, marks, logos, or branding as trademarks.

## Contributions

Do not submit proprietary third-party code, credentials, private DDC algorithms, or material you are not authorized to license. A future contributor agreement or contribution policy may add more specific terms.

## Commercial licensing

Commercial runtime, hosted-service, OEM, embedded, and enterprise licensing may be offered separately by Valentyn Rukhaylo / Altru.dev.

This policy is a repository licensing boundary, not legal advice. Organizations relying on it for commercial deployment should obtain their own legal review.
