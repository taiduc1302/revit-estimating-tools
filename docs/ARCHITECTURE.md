# Architecture

## Data flow

```text
Revit API
  -> pyRevit command
  -> read-only Revit adapter
  -> normalized element DTOs
  -> audit / aggregation
  -> deterministic snapshot
  -> integrity validation
  -> revision comparison
  -> estimator review / external downstream workflow
```

The deployable boundary is the single `RevitEstimating.extension/` folder. Its `lib/revit_estimating/` package contains the Revit API boundary (`collectors.py`, `parameters.py`, and `revit_adapter.py`) plus dependency-free core modules, while `config/categories.json` travels with the extension. Most core logic has no Autodesk dependency and can be unit-tested outside Revit.

## Design principles

1. **Read-only first.** No model transaction is required for V0.1.
2. **Evidence before automation.** Preserve source document, link context, UniqueId, ElementId and raw internal quantities.
3. **Normalize once.** Length, area and volume are normalized to metres, square metres and cubic metres.
4. **Deterministic exports.** Stable ordering and canonical JSON make review and hashing practical.
5. **Fail closed.** Unsupported schemas, duplicate identities, malformed/non-finite data and corrupted or internally inconsistent evidence packages stop compare/package workflows instead of producing partial results.
6. **No silent identity guessing.** Exact element keys are preferred. Recreated-element detection is explicitly labelled `POSSIBLE_RECREATED` with a confidence score.
7. **Estimator gate.** Outputs remain `NOT_ESTIMATOR_VALIDATED` until independently reviewed.
8. **Reproducible evidence.** Snapshot packages embed the exact governed category configuration, and review CSVs are deterministic derivatives of authoritative JSON rather than independent sources of truth.

## Identity model

Host elements use `HOST` scope plus Revit `UniqueId`. Linked elements use link-instance `UniqueId` plus element `UniqueId`, so repeated instances of the same linked model remain distinct. Model filenames and paths remain evidence fields but are not primary revision identity; a normal `Save As` should not redefine every host element.

Fallback fingerprints use logical scope, category, family/type, system/material, level, mark, size and approximate location. Fingerprint-based matches are never treated as exact identity and `POSSIBLE_RECREATED` requires reciprocal, unambiguous best candidates. For linked elements, representative location is published only when the link transform can be applied reliably; link-local points are not relabelled as host coordinates.

## Offline boundary

`tools/revit_estimating.py` exposes doctor/validate/compare/package/build-extension/benchmark workflows without Revit. The offline CLI imports the exact same runtime package from `RevitEstimating.extension/lib`; there is no second repository-level runtime copy. Golden snapshot fixtures exercise the same diff engine used by the pyRevit command. Validators recompute snapshot/comparison CSV evidence from authoritative JSON, and comparison validation can recompute the entire result from recorded baseline/current snapshots when those inputs remain available. This allows most transformation, identity, integrity and export behavior to be tested in CI; only the Autodesk API adapter and actual ribbon execution require a live Revit environment.

## Out of scope for V0.1

- pricing;
- automatic cost-code creation;
- AI classification;
- direct write-back to estimating software;
- editing Revit elements or parameters;
- certification that the BIM model is complete.
