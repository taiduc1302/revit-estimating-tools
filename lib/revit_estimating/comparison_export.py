# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import datetime
import os

from . import SCHEMA_VERSION, __version__
from .hashing import sha256_file
from .validation import snapshot_input_package_status
from .serialization import ensure_dir, write_json, write_csv
from .diff import flattened_change_rows

DELTA_COLUMNS = [
    "source_scope_key", "source_document", "baseline_source_document", "current_source_document",
    "category", "family", "type", "system", "material", "size", "unit",
    "baseline_quantity", "current_quantity", "delta"
]
CHANGE_COLUMNS = [
    "status", "source_document", "category", "element_key", "field", "before", "after", "confidence",
    "type", "primary_quantity_value", "primary_quantity_unit"
]


def _input_evidence(path):
    if not path:
        return None
    absolute = os.path.abspath(path)
    if not os.path.isfile(absolute):
        return {"path": absolute, "sha256": None, "status": "FILE_NOT_FOUND", "package_status": "FILE_NOT_FOUND"}
    return {"path": absolute, "sha256": sha256_file(absolute), "status": "HASHED", "package_status": snapshot_input_package_status(absolute)}


def _comparison_folder(output_root, stamp):
    base = os.path.join(output_root, "RevisionComparison_%s" % stamp)
    candidate = base
    index = 1
    while os.path.exists(candidate):
        candidate = "%s_v%03d" % (base, index)
        index += 1
    return ensure_dir(candidate)


def _stamp_from_created_at(created_at):
    return created_at.replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")


def write_revision_comparison(output_root, result, baseline_path=None, current_path=None, created_at=None):
    created_at = created_at or (datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    stamp = _stamp_from_created_at(created_at)
    folder = _comparison_folder(output_root, stamp)
    result_path = os.path.join(folder, "revision_diff.json")
    deltas_path = os.path.join(folder, "quantity_deltas.csv")
    changes_path = os.path.join(folder, "element_changes.csv")
    manifest_path = os.path.join(folder, "comparison_manifest.json")

    write_json(result_path, result)
    write_csv(deltas_path, result.get("quantity_deltas") or [], DELTA_COLUMNS)
    write_csv(changes_path, flattened_change_rows(result), CHANGE_COLUMNS)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool": "Revit Estimating Tools",
        "tool_version": __version__,
        "created_at": created_at,
        "status": "NOT_ESTIMATOR_VALIDATED",
        "baseline_snapshot": _input_evidence(baseline_path),
        "current_snapshot": _input_evidence(current_path),
        "summary": result.get("summary") or {},
        "evidence_hashes": {
            "revision_diff.json": sha256_file(result_path),
            "quantity_deltas.csv": sha256_file(deltas_path),
            "element_changes.csv": sha256_file(changes_path)
        }
    }
    write_json(manifest_path, manifest)
    return folder
