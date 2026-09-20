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
- `location` — representative host-coordinate point in metres where available
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

Comparison manifests record both the SHA-256 of each raw input and its `package_status`. When a source was recorded as `VALID_PACKAGE`, later comparison validation also re-checks that source package if the original input files are still available.

## Revision statuses

- `ADDED`
- `REMOVED`
- `MODIFIED`
- `UNCHANGED`
- `POSSIBLE_RECREATED`

`MODIFIED` includes selected classification, phase, workset, representative location, physical size, normalized quantity, aggregation status, and estimating-parameter changes.

`POSSIBLE_RECREATED` is inferred, never authoritative, and inferred matches are constrained to the same logical model/link scope.

Comparison may also emit warnings. `PROJECT_NUMBER_MISMATCH` is HIGH severity when both snapshots have non-empty Revit Project Number values and those values differ.

## Configuration provenance

`config/categories.json` is required at runtime. Extraction fails closed if it is missing, malformed, uses an unsupported schema version, contains duplicate names/BuiltInCategory mappings, declares an unsupported primary quantity, or uses non-boolean control flags.

The snapshot manifest `extraction_config.categories` object records:

- `path` — repository-relative config path;
- `sha256` — SHA-256 of the exact category config used;
- `schema_version` — category-config schema version;
- `category_count` — number of governed category specs loaded;
- `mode` — `REQUIRED_FAIL_CLOSED`.

Category specs are cached for the duration of the command so per-element audit rules do not repeatedly read the config file.

## Snapshot integrity

`manifest.json` records hashes for exported evidence files. Offline validation checks:

- all required package files exist;
- manifest and raw snapshot schema versions agree and are supported;
- category-configuration provenance is present, structurally valid, fail-closed, and consistent between manifest and raw snapshot metadata;
- every declared evidence hash matches the file on disk;
- optional `run_log.json`, when present, is declared and hashed;
- `elements` and `audit_issues` have the expected container types;
- `element_key` values are present and unique;
- `source_scope_key` is present for stable revision comparison;
- manifest/snapshot element and audit counts agree with exported records.

Use `python tools/revit_estimating.py validate <snapshot-folder>` or the focused `tools/validate_snapshot.py` command.

## Evidence/privacy note

`source_document_identity` may contain a full Revit model path, and `run_log.json` may contain the export path. These fields improve traceability but can expose internal filesystem/project information if a package is shared externally. V0.1 does not automatically redact paths.

## Validation status

All snapshot and comparison packages begin as `NOT_ESTIMATOR_VALIDATED`.
