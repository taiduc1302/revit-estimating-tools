# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import datetime
import os

from .hashing import sha256_file
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


def write_revision_comparison(output_root, result, baseline_path=None, current_path=None):
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    folder = ensure_dir(os.path.join(output_root, "RevisionComparison_%s" % stamp))
    result_path = os.path.join(folder, "revision_diff.json")
    deltas_path = os.path.join(folder, "quantity_deltas.csv")
    changes_path = os.path.join(folder, "element_changes.csv")
    manifest_path = os.path.join(folder, "comparison_manifest.json")

    write_json(result_path, result)
    write_csv(deltas_path, result.get("quantity_deltas") or [], DELTA_COLUMNS)
    write_csv(changes_path, flattened_change_rows(result), CHANGE_COLUMNS)
    manifest = {
        "schema_version": "0.1",
        "status": "NOT_ESTIMATOR_VALIDATED",
        "baseline_snapshot": baseline_path,
        "current_snapshot": current_path,
        "summary": result.get("summary") or {},
        "evidence_hashes": {
            "revision_diff.json": sha256_file(result_path),
            "quantity_deltas.csv": sha256_file(deltas_path),
            "element_changes.csv": sha256_file(changes_path)
        }
    }
    write_json(manifest_path, manifest)
    return folder
