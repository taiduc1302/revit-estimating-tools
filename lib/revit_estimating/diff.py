# -*- coding: utf-8 -*-
"""Deterministic snapshot revision comparison."""
from __future__ import absolute_import, division, print_function

from .aggregation import quantity_delta
from .fingerprint import similarity_score
from .utils import nested_get, is_number, to_text, rounded

COMPARISON_FIELDS = [
    "family", "type", "system", "material", "level", "workset", "phase_created",
    "phase_demolished", "design_option", "mark", "size.diameter_mm", "size.width_mm",
    "size.height_mm", "size.size_text", "quantities.length_m", "quantities.area_m2",
    "quantities.volume_m3", "primary_quantity_type", "primary_quantity_value", "primary_quantity_unit"
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
    return changes


def _infer_recreated(removed, added, threshold=0.75, ambiguity_gap=0.10):
    pairs = []
    used_added = set()
    for old in sorted(removed, key=lambda x: x.get("element_key", "")):
        candidates = []
        for new in added:
            if new.get("element_key") in used_added:
                continue
            score = similarity_score(old, new)
            if score > 0:
                candidates.append((score, new))
        candidates.sort(key=lambda item: (-item[0], item[1].get("element_key", "")))
        if not candidates or candidates[0][0] < threshold:
            continue
        best_score, best = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else 0.0
        if second_score and (best_score - second_score) < ambiguity_gap:
            continue
        used_added.add(best.get("element_key"))
        pairs.append({"baseline": old, "current": best, "confidence": rounded(best_score, 4)})
    return pairs


def compare_snapshots(baseline_snapshot, current_snapshot):
    baseline_elements = baseline_snapshot.get("elements") or []
    current_elements = current_snapshot.get("elements") or []
    baseline = dict((x.get("element_key"), x) for x in baseline_elements if x.get("element_key"))
    current = dict((x.get("element_key"), x) for x in current_elements if x.get("element_key"))

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
        "schema_version": "0.1",
        "summary": summary,
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
