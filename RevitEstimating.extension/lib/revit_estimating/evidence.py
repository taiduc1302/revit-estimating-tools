# -*- coding: utf-8 -*-
"""Deterministic derived evidence renderers shared by writers and validators."""
from __future__ import absolute_import, print_function

from .aggregation import aggregate_primary_quantities
from .audit import audit_summary
from .diff import flattened_change_rows
from .serialization import csv_text

ELEMENT_COLUMNS = [
    "element_key", "source_scope_key", "source_document", "source_document_identity", "is_linked",
    "link_instance_name", "link_instance_unique_id", "element_id", "unique_id", "category", "family", "type",
    "system", "material", "level", "workset", "phase_created", "phase_demolished", "design_option", "mark",
    "size", "location", "primary_quantity_type", "primary_quantity_value", "primary_quantity_unit",
    "quantity_aggregation_excluded", "quantities", "parameters", "fingerprints"
]
AUDIT_COLUMNS = ["issue_id", "severity", "rule_id", "source_document", "element_key", "element_id", "category", "message", "values"]
QUANTITY_COLUMNS = ["source_document", "category", "family", "type", "system", "material", "size", "unit", "quantity", "element_count"]
SUMMARY_COLUMNS = ["metric", "value"]

DELTA_COLUMNS = [
    "source_scope_key", "source_document", "baseline_source_document", "current_source_document",
    "category", "family", "type", "system", "material", "size", "unit",
    "baseline_quantity", "current_quantity", "delta"
]
CHANGE_COLUMNS = [
    "status", "source_document", "category", "element_key", "field", "before", "after", "confidence",
    "type", "primary_quantity_value", "primary_quantity_unit"
]


def snapshot_summary_rows(elements, audit_issues):
    summary = audit_summary(audit_issues)
    rows = [
        {"metric": "element_count", "value": len(elements)},
        {"metric": "audit_issue_count", "value": len(audit_issues)},
    ]
    for severity in ("HIGH", "MEDIUM", "LOW", "INFO"):
        rows.append({"metric": "audit_%s" % severity.lower(), "value": summary.get(severity, 0)})
    return rows


def snapshot_csv_texts(raw_snapshot):
    elements = raw_snapshot.get("elements") or []
    audit_issues = raw_snapshot.get("audit_issues") or []
    return {
        "elements.csv": csv_text(elements, ELEMENT_COLUMNS),
        "quantities.csv": csv_text(aggregate_primary_quantities(elements), QUANTITY_COLUMNS),
        "audit_issues.csv": csv_text(audit_issues, AUDIT_COLUMNS),
        "summary.csv": csv_text(snapshot_summary_rows(elements, audit_issues), SUMMARY_COLUMNS),
    }


def comparison_csv_texts(result):
    return {
        "quantity_deltas.csv": csv_text(result.get("quantity_deltas") or [], DELTA_COLUMNS),
        "element_changes.csv": csv_text(flattened_change_rows(result), CHANGE_COLUMNS),
    }
