# Threat Model

## Scope

This document covers V0.1 of Revit Estimating Tools: a local, read-only pyRevit extension that extracts estimating evidence, compares revisions, audits missing data, and packages results.

## Assets

Primary assets are:

1. **Revit model integrity** — commands must not modify or dirty the model.
2. **Quantity evidence integrity** — exported JSON/CSV, manifests, comparisons, and packages must fail closed when inconsistent.
3. **Deployment integrity** — the extension installed for live validation must match the CI-tested artifact.
4. **Estimator decision integrity** — inferred identity or incomplete extraction must never be presented as authoritative quantity truth.
5. **Filesystem/project privacy** — local model paths and project metadata must not be transmitted automatically.

## Trust boundaries

- Autodesk Revit API and the active document.
- pyRevit and its IronPython execution environment.
- linked Revit models.
- local filesystem and user-selected snapshot/comparison files.
- deterministic deployment ZIP and `deployment_manifest.json`.
- estimator review of warnings and reconciliations.

## Security invariants

Deployable V0.1 runtime must remain:

- offline: no HTTP, sockets, or other network clients;
- process-isolated: no shell/process spawning;
- static: no `eval`, `exec`, or dynamic import execution;
- read-only in Revit: no `Transaction`, `TransactionGroup`, or `SubTransaction`;
- explicit about incomplete extraction and identity uncertainty;
- fail-closed for unsupported schemas, duplicate identities, broken hashes, invalid config, and corrupted packages.

The standalone doctor checks these invariants before live use.

## Primary abuse / failure cases

### Malicious or formula-like BIM text

A parameter value beginning with spreadsheet formula syntax could execute when CSV is opened in Excel.

**Control:** CSV review exports prefix formula-like text; raw JSON retains the original evidence value.

### Tampered snapshot or comparison evidence

A file can be edited after extraction.

**Control:** SHA-256 evidence hashes, semantic validators, input-package revalidation, and fail-closed packaging.

### Tampered extracted deployment

Files can change after the deployment ZIP is extracted.

**Control:** `deployment_manifest.json` hashes every deployed runtime file; standalone doctor detects changed, missing, and undeclared files.

### Accidental model write-back

A future change could introduce Revit transactions.

**Control:** button contract tests and doctor transaction-token scan. Live validation also checks that commands do not dirty the model.

### Hidden network or process behavior

A future dependency or helper could transmit model metadata or invoke external tools.

**Control:** deployable Python is scanned for network modules, process spawning, and dynamic execution tokens; CI fails if introduced.

### Incomplete extraction reported as a valid zero

Revit API collection or per-element extraction can fail.

**Control:** failures are explicit audit findings; per-element extraction failures are HIGH severity. Invalid non-positive quantities do not reduce aggregate totals.

### Reinserted link interpreted as element continuity

A Revit link instance can receive a new scope identity.

**Control:** linked scope changes produce explicit warnings; inferred recreated matching never crosses logical scopes.

### Quadratic recreated-element inference

Large unmatched buckets could freeze comparison.

**Control:** candidate matching is capped per scope/category bucket; oversized buckets remain explicit ADDED/REMOVED with warning.

## Accepted limitations

- No digital signatures or external transparency log.
- Local administrators or repository writers can replace code and recompute hashes.
- Live Revit API semantics are not proven by offline CI.
- Exported evidence can contain local filesystem paths.
- English parameter-name fallbacks can remain relevant for some Revit families/environments.

These limitations are release-gated in `docs/RELEASE_CHECKLIST.md` and Issue #2.
