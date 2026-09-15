# -*- coding: utf-8 -*-
"""Quantity aggregation helpers."""
from __future__ import absolute_import, division, print_function

from .fingerprint import size_label
from .utils import to_text, is_number, rounded


def aggregation_key(element):
    return (
        to_text(element.get("source_document")),
        to_text(element.get("category")),
        to_text(element.get("family")),
        to_text(element.get("type")),
        to_text(element.get("system")),
        to_text(element.get("material")),
        size_label(element),
        to_text(element.get("primary_quantity_unit")),
    )


def aggregate_primary_quantities(elements):
    groups = {}
    for element in elements:
        value = element.get("primary_quantity_value")
        unit = element.get("primary_quantity_unit")
        if not unit or not is_number(value):
            continue
        key = aggregation_key(element)
        row = groups.setdefault(key, {"quantity": 0.0, "element_count": 0})
        row["quantity"] += float(value)
        row["element_count"] += 1
    result = []
    for key in sorted(groups.keys()):
        value = groups[key]
        result.append({
            "source_document": key[0], "category": key[1], "family": key[2],
            "type": key[3], "system": key[4], "material": key[5],
            "size": key[6], "unit": key[7],
            "quantity": rounded(value["quantity"]),
            "element_count": value["element_count"],
        })
    return result


def _revision_aggregation_key(element):
    scope = to_text(element.get("source_scope_key")).strip() or to_text(element.get("source_document"))
    return (
        scope,
        to_text(element.get("category")),
        to_text(element.get("family")),
        to_text(element.get("type")),
        to_text(element.get("system")),
        to_text(element.get("material")),
        size_label(element),
        to_text(element.get("primary_quantity_unit")),
    )


def _revision_aggregate(elements):
    groups = {}
    for element in elements:
        value = element.get("primary_quantity_value")
        unit = element.get("primary_quantity_unit")
        if not unit or not is_number(value):
            continue
        key = _revision_aggregation_key(element)
        row = groups.setdefault(key, {
            "quantity": 0.0,
            "element_count": 0,
            "source_document": to_text(element.get("source_document")),
        })
        row["quantity"] += float(value)
        row["element_count"] += 1
    return groups


def quantity_delta(baseline_elements, current_elements):
    """Aggregate revision deltas by stable source scope, not by RVT filename/path."""
    old = _revision_aggregate(baseline_elements)
    new = _revision_aggregate(current_elements)
    rows = []
    for key in sorted(set(old.keys()) | set(new.keys())):
        old_row = old.get(key, {})
        new_row = new.get(key, {})
        before = old_row.get("quantity", 0.0)
        after = new_row.get("quantity", 0.0)
        baseline_source = old_row.get("source_document", "")
        current_source = new_row.get("source_document", "")
        rows.append({
            "source_scope_key": key[0],
            "source_document": current_source or baseline_source,
            "baseline_source_document": baseline_source,
            "current_source_document": current_source,
            "category": key[1], "family": key[2],
            "type": key[3], "system": key[4], "material": key[5],
            "size": key[6], "unit": key[7],
            "baseline_quantity": rounded(before), "current_quantity": rounded(after),
            "delta": rounded(after - before),
        })
    return rows
