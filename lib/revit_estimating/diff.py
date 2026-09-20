# -*- coding: utf-8 -*-
"""Deterministic snapshot revision comparison."""
from __future__ import absolute_import, division, print_function

from . import SCHEMA_VERSION
from .aggregation import quantity_delta
from .fingerprint import similarity_score, size_label
from .utils import nested_get, is_number, to_text, rounded

COMPARISON_FIELDS = [
    "family", "type", "system", "material", "level", "workset", "phase_created",
    "phase_demolished", "design_option", "mark",
    "location.x_m", "location.y_m", "location.z_m",
    "quantities.length_m", "quantities.area_m2", "quantities.volume_m3",
    "primary_quantity_type", "primary_quantity_value", "primary_quantity_unit",
    "quantity_aggregation_excluded",
    "parameters.description", "parameters.comments", "parameters.type_comments",
    "parameters.assembly_code", "parameters.keynote", "parameters.model",
]


def _equal(left, right, tolerance=1e-6):
    if is_number(left) and is_number(right):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def field_changes(left, right):
    changes = []
    for field in COMPARISON_FIELDS:
        before = nested_get(left, field)
        after = nested_get(right, field)
        if not _equal(before, after):
            changes.append({"field": field, "before": before, "after": after})

    before_size = size_label(left)
    after_size = size_label(right)
    if before_size != after_size:
        changes.append({"field": "size", "before": before_size, "after": after_size})
    return changes


def _snapshot_elements(snapshot, label):
    if not isinstance(snapshot, dict):
        raise ValueError("%s snapshot must be a JSON object." % label)
    schema_version = to_text(snapshot.get("schema_version")).strip()
    if not schema_version:
        raise ValueError("%s snapshot is missing schema_version." % label)
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            "%s snapshot schema_version %s is not supported by this tool; expected %s."
            % (label, schema_version, SCHEMA_VERSION)
        )
    elements = snapshot.get("elements")
    if not isinstance(elements, list):
        raise ValueError("%s snapshot elements must be a list." % label)
    return elements


def _index_elements(elements, label):
    indexed = {}
    for position, element in enumerate(elements):
        if not isinstance(element, dict):
            raise ValueError("%s snapshot element at index %s is not an object." % (label, position))
        key = to_text(element.get("element_key")).strip()
        if not key:
            raise ValueError("%s snapshot element at index %s is missing element_key." % (label, position))
        if key in indexed:
            raise ValueError("%s snapshot contains duplicate element_key: %s" % (label, key))
        indexed[key] = element
    return indexed


def _project_number(snapshot):
    metadata = snapshot.get("metadata") or {}
    model = metadata.get("model") or {}
    return to_text(model.get("project_number")).strip()


def _project_name(snapshot):
    metadata = snapshot.get("metadata") or {}
    model = metadata.get("model") or {}
    return to_text(model.get("project_name")).strip()


def _comparison_warnings(baseline_snapshot, current_snapshot):
    warnings = []
    baseline_number = _project_number(baseline_snapshot)
    current_number = _project_number(current_snapshot)
    if baseline_number and current_number and baseline_number != current_number:
        warnings.append({
            "code": "PROJECT_NUMBER_MISMATCH",
            "severity": "HIGH",
            "message": "Baseline and current snapshots have different Revit project numbers. Confirm that these snapshots belong to the intended revision set.",
            "values": {"baseline_project_number": baseline_number, "current_project_number": current_number},
        })
        return warnings

    baseline_name = _project_name(baseline_snapshot)
    current_name = _project_name(current_snapshot)
    if baseline_name and current_name and baseline_name != current_name:
        same_number = bool(baseline_number and current_number and baseline_number == current_number)
        warnings.append({
            "code": "PROJECT_NAME_MISMATCH",
            "severity": "MEDIUM" if same_number else "HIGH",
            "message": "Baseline and current snapshots have different Revit project names. Confirm that these snapshots belong to the intended revision set.",
            "values": {
                "baseline_project_name": baseline_name,
                "current_project_name": current_name,
                "project_number": baseline_number if same_number else "",
            },
        })
    return warnings


def _unambiguous_best(candidates, threshold, ambiguity_gap):
    candidates = sorted(candidates, key=lambda item: (-item[0], item[1].get("element_key", "")))
    if not candidates or candidates[0][0] < threshold:
        return None
    best_score, best = candidates[0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0.0
    if second_score and (best_score - second_score) + 1e-9 < ambiguity_gap:
        return None
    return best_score, best


def _candidate_bucket(element):
    linked = bool(element.get("is_linked"))
    scope = to_text(element.get("source_scope_key")).strip()
    if not scope and linked:
        link_uid = to_text(element.get("link_instance_unique_id")).strip()
        if link_uid:
            scope = "LINK:%s" % link_uid
    return linked, scope, to_text(element.get("category")).strip().lower()


def _infer_recreated(removed, added, threshold=0.75, ambiguity_gap=0.10):
    """Return only reciprocal, unambiguous best matches to avoid greedy false positives."""
    added_by_bucket = {}
    for new in added:
        added_by_bucket.setdefault(_candidate_bucket(new), []).append(new)

    old_candidates = {}
    new_candidates = {}
    for old in removed:
        old_key = old.get("element_key")
        for new in added_by_bucket.get(_candidate_bucket(old), []):
            score = similarity_score(old, new)
            if score <= 0:
                continue
            old_candidates.setdefault(old_key, []).append((score, new))
            new_candidates.setdefault(new.get("element_key"), []).append((score, old))

    best_for_old = {}
    for old in removed:
        best = _unambiguous_best(old_candidates.get(old.get("element_key"), []), threshold, ambiguity_gap)
        if best is not None:
            best_for_old[old.get("element_key")] = best

    best_for_new = {}
    for new in added:
        best = _unambiguous_best(new_candidates.get(new.get("element_key"), []), threshold, ambiguity_gap)
        if best is not None:
            best_for_new[new.get("element_key")] = best

    pairs = []
    for old in sorted(removed, key=lambda x: x.get("element_key", "")):
        old_key = old.get("element_key")
        old_best = best_for_old.get(old_key)
        if old_best is None:
            continue
        score, new = old_best
        new_best = best_for_new.get(new.get("element_key"))
        if new_best is None or new_best[1].get("element_key") != old_key:
            continue
        pairs.append({"baseline": old, "current": new, "confidence": rounded(score, 4)})
    return pairs


def compare_snapshots(baseline_snapshot, current_snapshot):
    """Compare two compatible snapshots and fail closed on identity/schema defects."""
    baseline_elements = _snapshot_elements(baseline_snapshot, "Baseline")
    current_elements = _snapshot_elements(current_snapshot, "Current")
    baseline = _index_elements(baseline_elements, "Baseline")
    current = _index_elements(current_elements, "Current")

    exact_keys = sorted(set(baseline.keys()) & set(current.keys()))
    added_keys = sorted(set(current.keys()) - set(baseline.keys()))
    removed_keys = sorted(set(baseline.keys()) - set(current.keys()))

    modified = []
    unchanged_count = 0
    for key in exact_keys:
        changes = field_changes(baseline[key], current[key])
        if changes:
            modified.append({
                "status": "MODIFIED", "element_key": key,
                "source_document": current[key].get("source_document"),
                "category": current[key].get("category"), "changes": changes,
            })
        else:
            unchanged_count += 1

    removed = [baseline[key] for key in removed_keys]
    added = [current[key] for key in added_keys]
    recreated_pairs = _infer_recreated(removed, added)
    recreated_old = set(pair["baseline"].get("element_key") for pair in recreated_pairs)
    recreated_new = set(pair["current"].get("element_key") for pair in recreated_pairs)

    possible_recreated = []
    for pair in recreated_pairs:
        possible_recreated.append({
            "status": "POSSIBLE_RECREATED",
            "baseline_element_key": pair["baseline"].get("element_key"),
            "current_element_key": pair["current"].get("element_key"),
            "source_document": pair["current"].get("source_document"),
            "category": pair["current"].get("category"),
            "confidence": pair["confidence"],
            "changes": field_changes(pair["baseline"], pair["current"]),
        })

    final_removed = [
        {"status": "REMOVED", "element_key": x.get("element_key"), "source_document": x.get("source_document"),
         "category": x.get("category"), "type": x.get("type"), "primary_quantity_value": x.get("primary_quantity_value"),
         "primary_quantity_unit": x.get("primary_quantity_unit")}
        for x in removed if x.get("element_key") not in recreated_old
    ]
    final_added = [
        {"status": "ADDED", "element_key": x.get("element_key"), "source_document": x.get("source_document"),
         "category": x.get("category"), "type": x.get("type"), "primary_quantity_value": x.get("primary_quantity_value"),
         "primary_quantity_unit": x.get("primary_quantity_unit")}
        for x in added if x.get("element_key") not in recreated_new
    ]

    summary = {
        "ADDED": len(final_added), "REMOVED": len(final_removed), "MODIFIED": len(modified),
        "POSSIBLE_RECREATED": len(possible_recreated), "UNCHANGED": unchanged_count,
        "BASELINE_ELEMENTS": len(baseline_elements), "CURRENT_ELEMENTS": len(current_elements),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "warnings": _comparison_warnings(baseline_snapshot, current_snapshot),
        "added": final_added,
        "removed": final_removed,
        "modified": modified,
        "possible_recreated": possible_recreated,
        "quantity_deltas": quantity_delta(baseline_elements, current_elements),
        "baseline_metadata": baseline_snapshot.get("metadata") or {},
        "current_metadata": current_snapshot.get("metadata") or {},
    }


def flattened_change_rows(result):
    rows = []
    for group in ("added", "removed"):
        rows.extend(result.get(group) or [])
    for item in result.get("modified") or []:
        for change in item.get("changes") or []:
            rows.append({
                "status": "MODIFIED", "element_key": item.get("element_key"),
                "source_document": item.get("source_document"), "category": item.get("category"),
                "field": change.get("field"), "before": change.get("before"), "after": change.get("after")
            })
    for item in result.get("possible_recreated") or []:
        rows.append({
            "status": "POSSIBLE_RECREATED", "element_key": item.get("current_element_key"),
            "source_document": item.get("source_document"), "category": item.get("category"),
            "field": "identity", "before": item.get("baseline_element_key"), "after": item.get("current_element_key"),
            "confidence": item.get("confidence")
        })
    return rows
