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


def quantity_delta(baseline_elements, current_elements):
    def indexed(rows):
        data = {}
        for row in aggregate_primary_quantities(rows):
            key = tuple(row.get(k, "") for k in (
                "source_document", "category", "family", "type", "system", "material", "size", "unit"
            ))
            data[key] = row
        return data

    old = indexed(baseline_elements)
    new = indexed(current_elements)
    rows = []
    for key in sorted(set(old.keys()) | set(new.keys())):
        before = old.get(key, {}).get("quantity", 0.0)
        after = new.get(key, {}).get("quantity", 0.0)
        rows.append({
            "source_document": key[0], "category": key[1], "family": key[2],
            "type": key[3], "system": key[4], "material": key[5],
            "size": key[6], "unit": key[7],
            "baseline_quantity": rounded(before), "current_quantity": rounded(after),
            "delta": rounded(after - before),
        })
    return rows
