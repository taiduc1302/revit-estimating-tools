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
- SHA-256 provenance for the governed category configuration used by each extraction.
- Static IronPython-compatibility regression checks for runtime Python sources.

### Changed

- Host element identity no longer depends on RVT filename/path, so normal Save As operations do not redefine the entire model.
- Revision comparison now fails closed on unsupported/missing schema versions, duplicate element identities, malformed element collections, and invalid/orphaned snapshot packages; standalone inputs require an explicit CLI development override.
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
- Category configuration is required and fail-closed; silent built-in fallback was removed, specs are validated once and cached per command, and config provenance is embedded in snapshots.
- CSV review exports escape formula-like text so spreadsheet applications do not execute BIM text as formulas; numeric values remain numeric.
- Canonical JSON rejects non-finite numbers instead of emitting non-standard `NaN`/`Infinity` tokens.
- Snapshot validation enforces `NOT_ESTIMATOR_VALIDATED`, expected tool identity, and mirrored manifest/raw metadata consistency.
- Comparison validation keeps checking recorded input evidence structure even when original-file existence checks are explicitly skipped.
- `POSSIBLE_RECREATED` matching now requires reciprocal, unambiguous best candidates instead of greedy first-match assignment.
- Invalid non-positive primary quantities remain audited/evidenced but are excluded from aggregated totals and quantity deltas.
- Model/link audit issue IDs include source/trace values to avoid collisions across repeated link problems.
- Per-element extraction failures are HIGH severity because they can make quantity evidence incomplete.
- CLI package output is blocked from overwriting snapshot evidence files.
- Recreated-element inference is bounded per scope/category bucket; oversized candidate sets are skipped with an explicit warning instead of performing unbounded quadratic matching.
- Revision comparison validation reconciles summary counts and baseline/current totals against detailed result groups, including when original input-file checks are skipped.
- Snapshot CSV review evidence is recomputed from `raw_snapshot.json` during validation, and comparison CSVs are recomputed from `revision_diff.json`.
- When recorded comparison inputs are available, `revision_diff.json` is recomputed from baseline/current snapshots and must match.
- Project-name mismatch warnings provide a wrong-project fallback when Revit Project Number is blank or unavailable.
- Linked-model locations fail closed to `null` when a trustworthy transform is unavailable or fails, avoiding mislabeled link-local coordinates.
- JSON parsing rejects `NaN`/`Infinity`, and malformed derived evidence becomes a validator finding rather than an unhandled exception.
- Snapshot packages embed the exact governed category configuration and validate it against recorded SHA-256/schema/count provenance.

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
