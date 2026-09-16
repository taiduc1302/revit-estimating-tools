# -*- coding: utf-8 -*-
"""Snapshot package creation and downstream evidence exports."""
from __future__ import absolute_import, print_function

import os

from .aggregation import aggregate_primary_quantities
from .audit import audit_summary
from .hashing import sha256_file
from .manifest import next_snapshot_folder
from .serialization import ensure_dir, write_json, write_csv, read_json

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


def build_raw_snapshot(manifest, elements, audit_issues):
    metadata = dict(manifest)
    metadata.pop("evidence_hashes", None)
    return {
        "schema_version": manifest.get("schema_version"),
        "metadata": metadata,
        "elements": sorted(elements, key=lambda x: x.get("element_key", "")),
        "audit_issues": sorted(audit_issues, key=lambda x: x.get("issue_id", "")),
    }


def _summary_rows(elements, audit_issues):
    summary = audit_summary(audit_issues)
    rows = [
        {"metric": "element_count", "value": len(elements)},
        {"metric": "audit_issue_count", "value": len(audit_issues)},
    ]
    for severity in ("HIGH", "MEDIUM", "LOW", "INFO"):
        rows.append({"metric": "audit_%s" % severity.lower(), "value": summary.get(severity, 0)})
    return rows


def write_snapshot_package(output_root, manifest, elements, audit_issues):
    folder = ensure_dir(next_snapshot_folder(output_root, manifest.get("project_name") or "Model", manifest.get("created_at")))
    raw_path = os.path.join(folder, "raw_snapshot.json")
    elements_path = os.path.join(folder, "elements.csv")
    quantities_path = os.path.join(folder, "quantities.csv")
    issues_path = os.path.join(folder, "audit_issues.csv")
    summary_path = os.path.join(folder, "summary.csv")
    manifest_path = os.path.join(folder, "manifest.json")

    raw_snapshot = build_raw_snapshot(manifest, elements, audit_issues)
    write_json(raw_path, raw_snapshot)
    write_csv(elements_path, raw_snapshot["elements"], ELEMENT_COLUMNS)
    write_csv(quantities_path, aggregate_primary_quantities(elements), QUANTITY_COLUMNS)
    write_csv(issues_path, audit_issues, AUDIT_COLUMNS)
    write_csv(summary_path, _summary_rows(elements, audit_issues), SUMMARY_COLUMNS)

    evidence = {}
    for path in (raw_path, elements_path, quantities_path, issues_path, summary_path):
        evidence[os.path.basename(path)] = sha256_file(path)
    final_manifest = dict(manifest)
    final_manifest["evidence_hashes"] = evidence
    write_json(manifest_path, final_manifest)
    return folder


def load_raw_snapshot(path):
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        raise ValueError("Selected JSON is not a valid raw snapshot.")
    return data
