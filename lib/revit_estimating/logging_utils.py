# -*- coding: utf-8 -*-
"""Structured run-log helpers."""
from __future__ import absolute_import, print_function

import os

from .manifest import utc_now_iso
from .serialization import write_json


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
    return path
