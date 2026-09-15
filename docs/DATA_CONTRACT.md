# Data Contract

Schema version: `0.1`

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

`manifest.json` records hashes for exported evidence files. `tools/validate_snapshot.py` checks required files, hashes, duplicate element keys, and declared element count before packaging.

## Validation status

All snapshot and comparison packages begin as `NOT_ESTIMATOR_VALIDATED`.
