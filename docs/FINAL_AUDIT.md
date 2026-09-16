# Final Offline Audit — V0.1

Audit date: 2026-09-16

## Status

- `OFFLINE_VALIDATED`: pending final post-audit CI run
- `LIVE_REVIT_VALIDATED`: false
- `PRODUCTION_READY`: false until live Revit/pyRevit validation in Issue #2 is completed
- Model modification: not implemented
- Pricing/write-back: not implemented

This audit is a reviewer-style inspection of the repository, not a substitute for executing the extension inside Autodesk Revit.

## Audit scope

The audit reviewed:

- pyRevit extension/bundle structure and command contexts;
- read-only safety assumptions;
- Revit API parameter and collector usage;
- host/link identity and revision matching;
- quantity aggregation and audit-only behavior;
- snapshot/comparison evidence integrity;
- error handling and partial-extraction visibility;
- regression tests and CI coverage;
- neutral naming and absence of company-specific branding;
- estimator-facing failure modes such as wrong-project comparison and false quantity changes.

## Findings fixed during final audit

### Audit-only categories were still aggregating quantities

`Generic Models` is configured as `audit_only`, but that flag was not propagated into the DTO or aggregation layer. Audit-only elements now carry `quantity_aggregation_excluded: true` and are excluded from quantity summaries and revision quantity deltas while remaining available for model-audit review.

### Category collection failures could look like legitimate zero quantities

The Revit category collector previously returned an empty list for both a genuinely empty category and a Revit API/configuration exception. Collection failures now produce a HIGH `CATEGORY_COLLECTION_FAILED` audit issue and are recorded in `skipped_categories` metadata. Link-collection and unresolved-link-transform failures are also surfaced instead of being silent.

### Revision comparison missed movement and estimating metadata changes

Exact-identity elements could move or change classification metadata without becoming `MODIFIED`. Revision comparison now tracks representative host-coordinate location and selected estimating metadata including description, comments, type comments, Assembly Code, keynote, and model.

### Optional run log was packaged without integrity coverage

`run_log.json` could be included in the ZIP without a manifest hash. The run log is now registered in `evidence_hashes`; validation detects missing, unregistered, or tampered run-log evidence before packaging.

### CSV export omitted selected estimating parameters

`elements.csv` now includes the `parameters` object and `quantity_aggregation_excluded` flag so CSV review does not silently omit fields that exist in `raw_snapshot.json`.

### Pipe material extraction needed a stronger built-in fallback

The adapter now tries `RBS_PIPE_MATERIAL_PARAM` before generic material fallbacks.

### Wrong-project comparison needed an explicit guard

When both snapshots contain Revit Project Number values and they differ, comparison emits a HIGH `PROJECT_NUMBER_MISMATCH` warning. It remains a warning rather than an automatic rejection because project-number conventions vary and can legitimately be corrected between revisions.

### Ribbon commands needed user-facing failure handling

Model Audit, Extract Snapshot, and Compare Revision now catch top-level failures and show a controlled pyRevit alert rather than exposing a raw traceback as the normal user experience.

## Controls verified by automated tests

The automated suite covers or statically checks:

- deterministic normalization and serialization;
- stable host identity across file rename / Save As;
- separation of repeated Revit link instances;
- conservative recreated-element inference;
- duplicate identity and unsupported-schema rejection;
- numeric-size comparison independent of display-unit formatting;
- audit-only exclusion from quantity aggregation;
- movement and Assembly Code revision detection;
- snapshot hash tampering;
- run-log hash tampering;
- revision-comparison input/output hashes;
- collision-safe output folders;
- project-number mismatch warnings;
- expected pyRevit button structure, clean-engine metadata, project-document context, default IronPython assumption, and read-only transaction contract;
- absence of the removed company-specific project name in governed source/docs/config/tool paths.

## Known limitations that remain after offline audit

### Live Autodesk behavior is unverified

No offline test can prove actual Revit category enumeration, parameter availability on representative project families, linked-coordinate transforms, pyRevit ribbon loading, or that Revit's dirty state remains unchanged. These are the live gate in Issue #2.

### Source paths are evidence and may contain internal filesystem information

`source_document_identity` can contain the full local/model path and `run_log.json` can contain the chosen export path. Snapshot packages should therefore be treated as internal evidence unless paths are reviewed/redacted before external sharing. Automatic path-redaction is not implemented in V0.1.

### Localization fallbacks are not fully language-independent

Built-in Revit parameters are preferred, but several final fallback lookups use English display names such as `Material`, `Level`, and `System Type`. Phase heuristics for identifying an existing phase also use English text. Non-English Revit/model conventions require live validation.

### Material semantics vary by Revit category

A single `material` field is useful for estimating grouping but does not represent all compound-layer, painted-material, hosted-family, or multi-material cases. Walls/floors and complex families may need a material-breakdown feature in a later version.

### Representative location is not geometry equivalence

Location is a midpoint/point/bounding-box representative coordinate. It is useful for revision review and inferred matching, but it does not prove two element geometries are equivalent.

### Large-model performance is not benchmarked yet

The core algorithms are deterministic and dependency-light, but extraction and serialization have not been profiled on very large production models. Performance acceptance should be recorded during live validation.

### Open-model source file hashing is intentionally not claimed

The snapshot records `source_model_hash_status: NOT_COMPUTED_FOR_OPEN_MODEL`; V0.1 does not claim a SHA-256 hash of the active RVT file because the open document state and disk file may differ.

## Release gate

V0.1 may be considered **offline-ready** only after the final post-audit CI matrix is green. It must remain `NOT_ESTIMATOR_VALIDATED` / not production-ready until Issue #2 is completed on representative Autodesk Revit models.
