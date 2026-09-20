# -*- coding: utf-8 -*-
"""Snapshot package creation and downstream evidence exports."""
from __future__ import absolute_import, print_function

import os
import shutil

from .hashing import sha256_file
from .manifest import next_snapshot_folder
from .config import category_config_path
from .serialization import ensure_dir, write_json, write_text, read_json
from .evidence import snapshot_csv_texts

def build_raw_snapshot(manifest, elements, audit_issues):
    metadata = dict(manifest)
    metadata.pop("evidence_hashes", None)
    return {
        "schema_version": manifest.get("schema_version"),
        "metadata": metadata,
        "elements": sorted(elements, key=lambda x: x.get("element_key", "")),
        "audit_issues": sorted(audit_issues, key=lambda x: x.get("issue_id", "")),
    }


def write_snapshot_package(output_root, manifest, elements, audit_issues):
    folder = ensure_dir(next_snapshot_folder(output_root, manifest.get("project_name") or "Model", manifest.get("created_at")))
    raw_path = os.path.join(folder, "raw_snapshot.json")
    elements_path = os.path.join(folder, "elements.csv")
    quantities_path = os.path.join(folder, "quantities.csv")
    issues_path = os.path.join(folder, "audit_issues.csv")
    summary_path = os.path.join(folder, "summary.csv")
    manifest_path = os.path.join(folder, "manifest.json")
    category_config_evidence_path = os.path.join(folder, "categories_config.json")

    raw_snapshot = build_raw_snapshot(manifest, elements, audit_issues)
    write_json(raw_path, raw_snapshot)
    shutil.copyfile(category_config_path(), category_config_evidence_path)
    derived_csv = snapshot_csv_texts(raw_snapshot)
    write_text(elements_path, derived_csv["elements.csv"])
    write_text(quantities_path, derived_csv["quantities.csv"])
    write_text(issues_path, derived_csv["audit_issues.csv"])
    write_text(summary_path, derived_csv["summary.csv"])

    evidence = {}
    for path in (raw_path, elements_path, quantities_path, issues_path, summary_path, category_config_evidence_path):
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
