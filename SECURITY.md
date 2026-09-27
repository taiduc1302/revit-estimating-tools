# Security Policy

## Supported code

Security fixes apply to the current `main` branch and the active V0.1 development branch until V0.1 is released.

## Security model

Revit Estimating Tools V0.1 is intentionally local and read-only:

- no network access;
- no external process execution;
- no dynamic `eval` / `exec`;
- no Revit transactions or model write-back;
- no pricing, credential storage, or remote telemetry;
- exported evidence is marked `NOT_ESTIMATOR_VALIDATED` until the live validation gate is completed.

The offline doctor enforces these runtime constraints for deployable Python code.

## Reporting a vulnerability

Prefer GitHub's private vulnerability reporting / Security Advisory workflow when available. If a private channel is not available, open a minimal issue requesting private contact and do not include exploit details, credentials, private model data, or customer/project information in the public issue.

Useful report details include:

- affected commit or release;
- affected Revit / pyRevit versions;
- minimal reproduction steps;
- whether model integrity, evidence integrity, filesystem privacy, or deployment integrity is affected.

## Data privacy

Snapshot and comparison evidence may include local model paths and project metadata. Review exported packages before sharing outside the intended environment. V0.1 does not automatically redact filesystem paths.

## Integrity boundary

SHA-256 manifests detect drift only while the manifest itself is trusted. V0.1 does not digitally sign releases or evidence packages; a malicious actor with write access to both files and manifests can recompute hashes.
