# -*- coding: utf-8 -*-
"""Snapshot manifest builders."""
from __future__ import absolute_import, print_function

import datetime
import os

from . import __version__, SCHEMA_VERSION
from .serialization import sanitize_filename


def utc_now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def build_manifest(project_name, model_metadata, element_count, audit_count, extraction_config=None, created_at=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "Revit Estimating Tools",
        "tool_version": __version__,
        "status": "NOT_ESTIMATOR_VALIDATED",
        "created_at": created_at or utc_now_iso(),
        "project_name": project_name,
        "model": model_metadata or {},
        "element_count": int(element_count),
        "audit_issue_count": int(audit_count),
        "extraction_config": extraction_config or {},
        "evidence_hashes": {},
    }


def next_snapshot_folder(output_root, project_name, created_at=None):
    stamp = (created_at or utc_now_iso()).replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
    base = "%s_ModelSnapshot_%s" % (sanitize_filename(project_name), stamp)
    candidate = os.path.join(output_root, base)
    index = 1
    while os.path.exists(candidate):
        candidate = os.path.join(output_root, "%s_v%03d" % (base, index))
        index += 1
    return candidate
