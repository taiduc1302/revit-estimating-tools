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
  run_log.json
```

All exported snapshots start with status `NOT_ESTIMATOR_VALIDATED`.

## Safety model

Core extraction is read-only. Commands do not open Revit transactions or intentionally alter model elements, parameters, project settings, or links. Model audit findings are advisory and must be reviewed by a qualified estimator.

## Development status

V0.1 is an early development release. Automated tests validate the dependency-free core outside Revit, but live Revit/pyRevit validation is still required for supported Revit versions.
