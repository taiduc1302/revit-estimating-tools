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
- `size` — normalized dimensions where available
- `location` — representative host-coordinate point in metres where available
- `quantities` — raw Revit internal values plus normalized SI quantities
- `primary_quantity_type`, `primary_quantity_value`, `primary_quantity_unit`
- `fingerprints` — strict/loose comparison fingerprints

## Units

- `M` — metres
- `M2` — square metres
- `M3` — cubic metres
- `EA` — count / each

## Revision statuses

- `ADDED`
- `REMOVED`
- `MODIFIED`
- `UNCHANGED`
- `POSSIBLE_RECREATED`

`POSSIBLE_RECREATED` is inferred, never authoritative, and inferred matches are constrained to the same logical model/link scope.

## Snapshot integrity

`manifest.json` records hashes for exported evidence files. Offline validation checks:

- all required package files exist;
- manifest and raw snapshot schema versions agree and are supported;
- every declared evidence hash matches the file on disk;
- `elements` and `audit_issues` have the expected container types;
- `element_key` values are present and unique;
- `source_scope_key` is present for stable revision comparison;
- manifest/snapshot element and audit counts agree with exported records.

Use `python tools/revit_estimating.py validate <snapshot-folder>` or the focused `tools/validate_snapshot.py` command.

## Validation status

All snapshot and comparison packages begin as `NOT_ESTIMATOR_VALIDATED`.
