# Changelog

All notable changes to this project will be documented here.

## 0.1.0 - Unreleased

### Added

- pyRevit **Estimating** tab with Model Audit, Extract Snapshot, Compare Revision, and Estimating Package commands.
- Read-only extraction from host and loaded linked Revit models.
- Normalized Length, Area, Volume, and Count quantities.
- Estimating-oriented model audit rules and severity levels.
- Deterministic JSON/CSV snapshot packages and SHA-256 evidence hashes.
- Stable revision identity using logical host/link scope plus Revit `UniqueId`.
- Conservative `POSSIBLE_RECREATED` matching constrained to the same source scope.
- Revision quantity deltas with baseline/current source-document evidence.
- Offline snapshot integrity validation.
- Unified offline CLI for validate / compare / package workflows.
- Golden baseline/current snapshot fixtures and regression comparison.
- Revision comparison manifests with hashes of both input snapshots and generated evidence files.
- GitHub Actions matrix tests on Python 3.8, 3.11, and 3.12.
- Static extension safety contract tests for read-only commands, bundle metadata, engine choice, and neutral naming.
- Revit/pyRevit API compatibility notes.

### Changed

- Host element identity no longer depends on RVT filename/path, so normal Save As operations do not redefine the entire model.
- Revision comparison now fails closed on unsupported/missing schema versions, duplicate element identities, and malformed element collections.
- Estimating Package validates snapshot integrity before creating a ZIP.
- Revit metadata lookup is centralized in the adapter.
- MEP extraction includes additional Revit 2026 level, service/system, size, length, and volume fallbacks.
- Revision comparison output directories are collision-safe and version themselves when timestamps collide.

### Validation status

- Dependency-free core and offline workflows are covered by automated tests.
- Live Autodesk Revit / pyRevit behavior remains `NOT_ESTIMATOR_VALIDATED` until Issue #2 is completed on a representative model.

### Out of scope for 0.1.0

- Revit model modification.
- Pricing.
- AI classification.
- Automatic cost-code creation.
- Direct write-back to estimating systems.
