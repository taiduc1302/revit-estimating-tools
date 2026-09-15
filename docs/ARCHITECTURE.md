# Architecture

## Data flow

```text
Revit API
  -> pyRevit command
  -> read-only Revit adapter
  -> normalized element DTOs
  -> audit / aggregation
  -> deterministic snapshot
  -> revision comparison
  -> estimator review / external downstream workflow
```

The Revit API boundary is isolated in `collectors.py`, `parameters.py`, and `revit_adapter.py`. Most core logic has no Autodesk dependency and can be unit-tested outside Revit.

## Design principles

1. **Read-only first.** No model transaction is required for V0.1.
2. **Evidence before automation.** Preserve source document, link context, UniqueId, ElementId and raw internal quantities.
3. **Normalize once.** Length, area and volume are normalized to metres, square metres and cubic metres.
4. **Deterministic exports.** Stable ordering and canonical JSON make review and hashing practical.
5. **No silent identity guessing.** Exact element keys are preferred. Recreated-element detection is explicitly labelled `POSSIBLE_RECREATED` with a confidence score.
6. **Estimator gate.** Outputs remain `NOT_ESTIMATOR_VALIDATED` until independently reviewed.

## Identity model

Host elements use source-document identity plus Revit `UniqueId`. Linked elements also include link-instance `UniqueId` so repeated instances of the same linked model are not silently collapsed.

Fallback fingerprints use category, family/type, system/material, level, mark, size and approximate location. Fingerprint-based matches are never treated as exact identity.

## Out of scope for V0.1

- pricing;
- automatic cost-code creation;
- AI classification;
- direct write-back to estimating software;
- editing Revit elements or parameters;
- certification that the BIM model is complete.
