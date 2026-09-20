# Data Contract

Schema version: `0.1`

## Compatibility rule

Snapshot comparison is fail-closed. Both snapshots must declare the currently supported `schema_version`, their `elements` value must be a list, and every element must have a unique non-empty `element_key`. Unsupported or missing schema versions and duplicate identities stop comparison instead of producing a partial delta report.

## Element identity

- `element_key` — logical source scope plus Revit `UniqueId` (or ElementId fallback).
- `source_scope_key` — `HOST` for host elements and `LINK:<link instance UniqueId>` for linked elements when available.
- `source_document` — Revit document title at extraction time.
- `source_document_identity` — diagnostic path/title evidence only; it is not the primary revision key.
- `is_linked` and `link_instance_*` — preserve linked-model context and keep repeated link instances distinct.
- `element_id` — navigation/debug identifier, not treated as globally stable.
- `unique_id` — exact Revit identity inside a logical source scope.

This design prevents a simple `Save As` or filename change from turning an otherwise unchanged host model into all-added/all-removed elements.

## Estimating fields

- `category`, `family`, `type`, `system`, `material`, `level`, `workset`, `phase_created`, `phase_demolished`, `design_option`, `mark`
- `size` — normalized physical dimensions where available; formatted `size_text` is only a fallback when numeric dimensions are unavailable
- `location` — representative host-coordinate point in metres where available. Linked elements publish no location when a trustworthy link transform is unavailable or cannot be applied; link-local coordinates are never relabelled as host coordinates.
- `quantities` — raw Revit internal values plus normalized SI quantities
- `primary_quantity_type`, `primary_quantity_value`, `primary_quantity_unit`
- `quantity_aggregation_excluded` — true for audit-only categories; these elements remain in evidence/audit data but do not contribute to quantity aggregation or revision quantity deltas
- `parameters` — selected estimating metadata: description, instance/type comments, Assembly Code, keynote, and model
- `fingerprints` — strict/loose comparison fingerprints used only for conservative inferred recreated-element matching

## Units

- `M` — metres
- `M2` — square metres
- `M3` — cubic metres
- `EA` — count / each

## Revision input trust

The pyRevit Compare Revision command requires both inputs to be `raw_snapshot.json` files inside intact snapshot packages that pass `validate_snapshot_folder()`. A tampered, partial, moved-alone, or orphaned raw snapshot is rejected before comparison. The offline CLI uses the same default; `--allow-standalone` exists only for fixtures/development and is recorded in comparison evidence as `STANDALONE_UNVERIFIED`.

Comparison manifests record both the SHA-256 of each raw input and its `package_status`. When a source was recorded as `VALID_PACKAGE`, later comparison validation also re-checks that source package if the original input files are still available. Comparison validation also recomputes `quantity_deltas.csv` and `element_changes.csv` from `revision_diff.json`; when the original baseline/current snapshots are still available, it recomputes the full revision result and requires it to match `revision_diff.json`.

## Revision statuses

- `ADDED`
- `REMOVED`
- `MODIFIED`
- `UNCHANGED`
- `POSSIBLE_RECREATED`

`MODIFIED` includes selected classification, phase, workset, representative location, physical size, normalized quantity, aggregation status, and estimating-parameter changes.

`POSSIBLE_RECREATED` is inferred, never authoritative, and inferred matches are constrained to the same logical model/link scope. A pair is emitted only when baseline and current elements are reciprocal, unambiguous best candidates above the configured confidence threshold. To prevent pathological quadratic work on large revisions, inference is skipped for any single scope/category bucket exceeding 250,000 candidate pairs; those elements remain explicit `ADDED`/`REMOVED` records and the comparison emits `RECREATED_MATCH_SKIPPED_LARGE_BUCKET`.

Comparison may also emit warnings. `PROJECT_NUMBER_MISMATCH` is HIGH severity when both snapshots have non-empty Revit Project Number values and those values differ. When project numbers do not establish identity, differing non-empty Revit Project Name values emit `PROJECT_NAME_MISMATCH` (HIGH when project numbers are blank/unavailable, MEDIUM when the same populated project number is present on both snapshots).

## Configuration provenance

`config/categories.json` is required at runtime. Extraction fails closed if it is missing, malformed, uses an unsupported schema version, contains duplicate names/BuiltInCategory mappings, declares an unsupported primary quantity, or uses non-boolean control flags.

Each snapshot also embeds the exact governed category configuration as `categories_config.json`; its file SHA-256 must match both the manifest evidence hash and `extraction_config.categories.sha256`. This keeps the actual extraction rules recoverable with the snapshot instead of storing only an unverifiable historical digest.

The snapshot manifest `extraction_config.categories` object records:

- `path` — repository-relative config path;
- `sha256` — SHA-256 of the exact category config used;
- `schema_version` — category-config schema version;
- `category_count` — number of governed category specs loaded;
- `mode` — `REQUIRED_FAIL_CLOSED`.

Category specs are cached for the duration of the command so per-element audit rules do not repeatedly read the config file.

## Snapshot integrity

`manifest.json` records hashes for exported evidence files. Offline validation also requires the manifest status to remain `NOT_ESTIMATOR_VALIDATED` and checks that mirrored manifest metadata agrees with the metadata inside hashed `raw_snapshot.json`. Offline validation checks:

- all required package files exist, including the embedded `categories_config.json` used for extraction;
- manifest and raw snapshot schema versions agree and are supported;
- category-configuration provenance is present, structurally valid, fail-closed, and consistent between manifest and raw snapshot metadata;
- every declared evidence hash matches the file on disk;
- optional `run_log.json`, when present, is declared and hashed;
- `elements` and `audit_issues` have the expected container types;
- `element_key` values are present and unique;
- `source_scope_key` is present for stable revision comparison;
- manifest/snapshot element and audit counts agree with exported records;
- manifest identity/status metadata agrees with hashed raw snapshot metadata;
- `elements.csv`, `quantities.csv`, `audit_issues.csv`, and `summary.csv` are recomputed from `raw_snapshot.json` and must match exactly, so merely changing a CSV and updating its hash is not sufficient.

Use `python tools/revit_estimating.py validate <snapshot-folder>` or the focused `tools/validate_snapshot.py` command.

## Evidence/privacy note

`source_document_identity` may contain a full Revit model path, `run_log.json` may contain the export path, and comparison manifests record absolute baseline/current snapshot paths so they can be revalidated later. These fields improve traceability but can expose internal filesystem/project information if a package is shared externally. V0.1 does not automatically redact paths.

SHA-256 evidence hashes provide corruption/tamper detection only while the manifest itself is trusted. V0.1 does not digitally sign manifests and therefore does not provide cryptographic authenticity against an actor who can edit the manifest and recompute every evidence hash. External signing or a trusted immutable hash registry is a later governance capability.

CSV exports are spreadsheet-safe review surfaces: formula-like text values are prefixed so Excel does not execute them as formulas. `raw_snapshot.json` remains the authoritative unmodified evidence representation for those text values. JSON writing and reading reject non-finite `NaN` / `Infinity` values so exported evidence stays within strict JSON numeric semantics.

## Validation status

All snapshot and comparison packages begin as `NOT_ESTIMATOR_VALIDATED`.
