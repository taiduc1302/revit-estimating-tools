# Data Contract

Schema version: `0.1`

## Element record

Key fields:

- `element_key` — repository-defined stable key combining source-document identity, optional link-instance identity, and Revit UniqueId.
- `source_document` / `source_document_identity` — model origin.
- `is_linked` — whether the element came from a loaded Revit link.
- `link_instance_*` — link-instance context for linked elements.
- `element_id` — Revit ElementId for debugging/navigation; not treated as globally stable identity.
- `unique_id` — Revit UniqueId.
- `category`, `family`, `type`, `system`, `material`, `level`, `workset`, `phase_created`, `phase_demolished`, `design_option`, `mark` — estimating context.
- `size` — normalized dimensions where available.
- `location` — representative host-coordinate point in metres where available.
- `quantities` — raw Revit internal quantity values and normalized SI values.
- `primary_quantity_type`, `primary_quantity_value`, `primary_quantity_unit` — configured primary takeoff quantity.
- `fingerprints` — strict/loose comparison fingerprints.

## Units

- `M` — metres
- `M2` — square metres
- `M3` — cubic metres
- `EA` — count / each

Raw Revit internal length/area/volume values are retained in the `quantities` object for auditability.

## Audit issue

Each issue has `issue_id`, `rule_id`, `severity`, element/source identity, a human-readable message and relevant values.

Severities: `HIGH`, `MEDIUM`, `LOW`, `INFO`.

## Revision statuses

- `ADDED`
- `REMOVED`
- `MODIFIED`
- `UNCHANGED`
- `POSSIBLE_RECREATED`

`POSSIBLE_RECREATED` is inferred, not authoritative.

## Validation status

All snapshot and comparison packages begin as:

`NOT_ESTIMATOR_VALIDATED`
