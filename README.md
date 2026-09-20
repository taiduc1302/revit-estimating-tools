# Revit Estimating Tools

Read-only estimating utilities for Autodesk Revit built on pyRevit.

## V0.1 scope

The first release focuses on four commands inside an **Estimating** tab:

- **Model Audit** — flags estimating-related model data issues.
- **Extract Snapshot** — exports normalized model data and audit evidence to JSON/CSV.
- **Compare Revision** — compares two snapshots and reports element and quantity changes.
- **Estimating Package** — creates a portable ZIP from an exported snapshot.

The project deliberately does **not** modify Revit model data, price work, create cost codes, or write directly into an estimating system.

## Installation

1. Install a compatible pyRevit 6.5.x release.
2. Clone this repository to a local folder.
3. Add the repository folder as a pyRevit custom extension search path, or place/symlink `RevitEstimating.extension` in a configured pyRevit extensions directory while preserving access to the repository `lib` and `config` folders.
4. Reload pyRevit.
5. Open Revit and use the **Estimating** tab.

`config/categories.json` is a governed runtime input, not an optional convenience file. Model Audit and Extract Snapshot fail closed if it is missing, malformed, schema-incompatible, or internally inconsistent. Each snapshot records the config path, schema version, category count, and SHA-256 used for that extraction.

For development setup and validation details see `docs/DEVELOPMENT.md` and `docs/TESTING.md`.

## Snapshot output

A snapshot package contains:

```text
<Project>_ModelSnapshot_<timestamp>/
  manifest.json
  raw_snapshot.json
  elements.csv
  quantities.csv
  audit_issues.csv
  summary.csv
  categories_config.json
  run_log.json
```

All exported snapshots start with status `NOT_ESTIMATOR_VALIDATED`.

## Offline CLI

The dependency-free core can be used without Autodesk Revit:

```bash
python tools/revit_estimating.py validate <snapshot-folder>
python tools/revit_estimating.py compare baseline/raw_snapshot.json current/raw_snapshot.json --output comparisons
python tools/revit_estimating.py validate-comparison <RevisionComparison_folder>
python tools/revit_estimating.py package <snapshot-folder>
```

Add `--json` to any command for machine-readable output. Compare requires each `raw_snapshot.json` to remain inside an intact snapshot package whose manifest/evidence hashes validate. `--allow-standalone` is an explicit development/fixture escape hatch and should not be used for production evidence. `validate-comparison` checks generated comparison evidence and the exact baseline/current input hashes; add `--skip-input-files` when the original input files have intentionally been moved and only the generated comparison package should be verified.

Comparison rejects unsupported snapshot schema versions and duplicate element identities instead of silently producing a partial result. The older `tools/validate_snapshot.py` entry point remains available as a focused snapshot-validator command.

## Revision identity

Revision comparison uses stable logical scope plus Revit `UniqueId`:

- host elements: `HOST:<UniqueId>`;
- linked elements: `LINK:<link-instance-UniqueId>:<UniqueId>`.

The RVT filename/path is retained as evidence but is not part of the primary comparison identity, so normal `Save As` or filename changes do not redefine every host element. Inferred recreated-element matches are constrained to the same host/link scope and remain labelled `POSSIBLE_RECREATED`.

Physical numeric dimensions are authoritative for size comparison and aggregation. Revit-formatted `size_text` is used only as a fallback when numeric dimensions are unavailable, preventing display-unit changes such as `300 mm` to `0.30 m` from creating false revisions.

## Safety model

Core extraction is read-only. Commands do not open Revit transactions or intentionally alter model elements, parameters, project settings, or links. Snapshot packaging performs integrity validation first. Model audit and inferred revision matches are advisory and must be reviewed by a qualified estimator.

## Development status

V0.1 is an early development release. Automated tests, golden fixtures and offline integrity checks validate the dependency-free core outside Revit, but live Revit/pyRevit validation is still required before production use.
