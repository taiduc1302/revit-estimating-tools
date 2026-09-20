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
3. Either add the repository root as a pyRevit custom extension search path **or** copy/symlink the single `RevitEstimating.extension` folder into any configured pyRevit extensions directory.
4. Reload pyRevit.
5. Open Revit and use the **Estimating** tab.

`RevitEstimating.extension` is self-contained: its runtime package lives under `lib/revit_estimating` and its governed category configuration lives under `config/categories.json`. No repository-level `lib` or `config` folder is required after deployment. Model Audit and Extract Snapshot fail closed if the embedded category config is missing, malformed, schema-incompatible, or internally inconsistent.

For deployment details see `docs/INSTALLATION.md`; for development and validation see `docs/DEVELOPMENT.md` and `docs/TESTING.md`. The guarded release process is documented in `docs/RELEASE_CHECKLIST.md`.

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
python tools/revit_estimating.py build-extension --output dist/RevitEstimating.extension.zip --json
python tools/revit_estimating.py benchmark --elements 20000 --replacements 600 --json
```

Add `--json` to any command for machine-readable output. Compare requires each `raw_snapshot.json` to remain inside an intact snapshot package whose manifest/evidence hashes validate. `--allow-standalone` is an explicit development/fixture escape hatch and should not be used for production evidence. `validate-comparison` checks generated comparison evidence and the exact baseline/current input hashes; add `--skip-input-files` when the original input files have intentionally been moved and only the generated comparison package should be verified.

Comparison rejects unsupported snapshot schema versions and duplicate element identities instead of silently producing a partial result. `build-extension` runs the offline doctor and creates a deterministic ZIP containing only the self-contained pyRevit extension. The `benchmark` command generates synthetic snapshots entirely offline and reports comparison throughput; it is intended as a regression/performance signal, not as a substitute for live Revit extraction benchmarking. The older `tools/validate_snapshot.py` entry point remains available as a focused snapshot-validator command.

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
