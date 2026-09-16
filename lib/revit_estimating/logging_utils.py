# -*- coding: utf-8 -*-
"""Structured run-log helpers."""
from __future__ import absolute_import, print_function

import os

from .hashing import sha256_file
from .manifest import utc_now_iso
from .serialization import read_json, write_json


def build_run_record(command, model, started_at, element_count=0, warning_count=0, error_count=0, export_path=None, tool_version=None):
    return {
        "command": command,
        "model": model,
        "started_at": started_at,
        "ended_at": utc_now_iso(),
        "tool_version": tool_version,
        "element_count": int(element_count or 0),
        "warning_count": int(warning_count or 0),
        "error_count": int(error_count or 0),
        "export_path": export_path,
    }


def write_run_log(folder, record):
    path = os.path.join(folder, "run_log.json")
    write_json(path, record)

    # The run log is packaged downstream, so register it as evidence instead of
    # allowing an unhashed optional file into an otherwise integrity-checked ZIP.
    manifest_path = os.path.join(folder, "manifest.json")
    if os.path.isfile(manifest_path):
        manifest = read_json(manifest_path)
        evidence = manifest.get("evidence_hashes")
        if not isinstance(evidence, dict):
            evidence = {}
            manifest["evidence_hashes"] = evidence
        evidence["run_log.json"] = sha256_file(path)
        write_json(manifest_path, manifest)
    return path
