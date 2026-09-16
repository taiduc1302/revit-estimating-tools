# Testing

## Automated tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the dependency-free suite on supported Python versions, compiles core/tests/tools, and executes a golden revision comparison through the offline CLI.

## Golden fixtures

`tests/fixtures/baseline_snapshot.json` and `tests/fixtures/current_snapshot.json` provide a fixed regression case with:

- one modified pipe quantity;
- one removed wall;
- one added floor;
- one unchanged linked conduit;
- a host-model filename change between revisions.

Expected summary: 1 added, 1 removed, 1 modified, 0 possible-recreated, 1 unchanged. The fixture verifies that filename changes do not redefine host element identity and that quantity deltas remain stable.

## Offline commands

```bash
python tools/revit_estimating.py compare tests/fixtures/baseline_snapshot.json tests/fixtures/current_snapshot.json --output .ci-output
python tools/revit_estimating.py validate <snapshot-folder>
python tools/revit_estimating.py package <snapshot-folder>
```

Comparison must fail on unsupported/missing schema versions and duplicate element keys. Packaging must fail if snapshot integrity validation reports any finding.

## Live Revit validation checklist

Automated tests do not replace a Revit test. Before calling a release production-ready, validate on representative models:

1. tab and all four buttons load in pyRevit;
2. Model Audit completes without starting a Revit transaction;
3. host and loaded links are discovered correctly;
4. supported categories extract expected family/type/system/material/level data;
5. Revit internal units normalize correctly against known measurements;
6. link-instance transforms produce sensible host-coordinate locations;
7. unloaded links are flagged;
8. snapshot files open and hashes validate;
9. two controlled revisions produce expected added/removed/modified results;
10. `Save As` / filename changes preserve host element identity;
11. repeated instances of one linked model stay distinct;
12. no model dirty-state change is caused by the extension.

Record Revit build, pyRevit version, model type and observed discrepancies for every live validation.
