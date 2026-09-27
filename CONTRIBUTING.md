# Contributing

Thanks for improving Revit Estimating Tools.

V0.1 is intentionally narrow: a local, read-only pyRevit estimating evidence toolkit. Changes should preserve that contract unless a future version explicitly changes scope.

## Before changing code

Read:

- `README.md`
- `SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_CONTRACT.md`
- `docs/THREAT_MODEL.md`
- `docs/RELEASE_CHECKLIST.md`

## V0.1 invariants

Contributions must preserve:

- no Revit write transactions;
- no network access or telemetry;
- no external process execution;
- no dynamic `eval` / `exec`;
- no pricing or automatic cost-code write-back;
- default IronPython compatibility for pyRevit button scripts;
- dependency-free core runtime;
- fail-closed behavior for invalid config, unsupported schema, duplicate identities, corrupted evidence, and incomplete package inputs;
- `NOT_ESTIMATOR_VALIDATED` outputs until the live gate is completed;
- no company-specific or live tender/project branding in source, fixtures, docs, or tests.

## Source of truth

The deployable runtime lives under:

```text
RevitEstimating.extension/
```

Do not reintroduce repository-level duplicate runtime/config folders.

## Local checks

Run:

```text
python tools/revit_estimating.py doctor --json
python -m unittest discover -s tests -v
python tools/revit_estimating.py compare tests/fixtures/baseline_snapshot.json tests/fixtures/current_snapshot.json --output .local-output --allow-standalone --json
python tools/revit_estimating.py build-extension --output .local-output/RevitEstimating.extension.zip --json
python tools/revit_estimating.py benchmark --elements 10000 --replacements 600 --max-seconds 30 --json
python -m compileall -q RevitEstimating.extension/lib tests tools
```

## Revit-dependent changes

A green offline CI run does not prove Autodesk Revit behavior.

Changes affecting Revit API extraction, parameter semantics, linked transforms, quantity semantics, pyRevit engine behavior, or model dirty state require live validation before release approval. Use the live-validation kit/report workflow and update Issue #2 evidence.

## Tests

Add regression coverage for every bug or contract change. Prefer tests that fail closed rather than tests that merely assert a happy path.

## Security reports

Follow `SECURITY.md`. Do not publish exploit details, private model data, credentials, or customer/project information in a public issue.
