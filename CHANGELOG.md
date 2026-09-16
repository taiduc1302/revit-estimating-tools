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
- Offline snapshot and revision-comparison integrity validation.
- Unified offline CLI for doctor / validate / compare / validate-comparison / package workflows.
- Golden baseline/current snapshot fixtures and regression comparison.
- Revision comparison manifests with hashes of both input snapshots and generated evidence files.
- GitHub Actions matrix tests on Python 3.8, 3.11, and 3.12.
- Static extension safety contract tests for read-only commands, bundle metadata, engine choice, context, and neutral naming.
- Revit/pyRevit API compatibility notes and a final offline audit report.
- HIGH `PROJECT_NUMBER_MISMATCH` warning for suspicious cross-project revision comparisons.

### Changed

- Host element identity no longer depends on RVT filename/path, so normal Save As operations do not redefine the entire model.
- Revision comparison now fails closed on unsupported/missing schema versions, duplicate element identities, and malformed element collections.
- Revision comparison now detects representative-location and selected estimating-parameter changes.
- Physical numeric size is authoritative over formatted size text to avoid false changes caused by display-unit formatting.
- Audit-only categories remain reviewable evidence but are excluded from aggregated quantities and quantity deltas.
- Revit category/link collection failures are surfaced as audit findings rather than silently treated as empty model scope.
- `elements.csv` now includes selected estimating parameters and the quantity-aggregation exclusion flag.
- `run_log.json`, when present, is included in manifest integrity hashes and validated before packaging.
- Estimating Package validates snapshot integrity before creating a ZIP.
- Revit metadata lookup is centralized in the adapter.
- MEP extraction includes additional Revit 2026 level, service/system, size, length, volume, and pipe-material fallbacks.
- Revision comparison output directories are collision-safe and version themselves when timestamps collide.
- Ribbon commands provide controlled user-facing alerts on top-level failures.

### Validation status

- Dependency-free core and offline workflows are covered by automated tests.
- Final offline audit findings are documented in `docs/FINAL_AUDIT.md`.
- Live Autodesk Revit / pyRevit behavior remains `NOT_ESTIMATOR_VALIDATED` until Issue #2 is completed on a representative model.

### Out of scope for 0.1.0

- Revit model modification.
- Pricing.
- AI classification.
- Automatic cost-code creation.
- Direct write-back to estimating systems.
