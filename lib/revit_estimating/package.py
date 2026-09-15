# -*- coding: utf-8 -*-
"""Create a portable ZIP from a validated snapshot folder."""
from __future__ import absolute_import, print_function

import os
import zipfile

REQUIRED_FILES = ("manifest.json", "raw_snapshot.json", "elements.csv", "quantities.csv", "audit_issues.csv", "summary.csv")


def validate_snapshot_folder(folder):
    missing = [name for name in REQUIRED_FILES if not os.path.isfile(os.path.join(folder, name))]
    if missing:
        raise ValueError("Snapshot folder is missing required files: %s" % ", ".join(missing))
    return True


def create_estimating_package(snapshot_folder, output_path=None):
    validate_snapshot_folder(snapshot_folder)
    if output_path is None:
        output_path = snapshot_folder.rstrip("\\/") + "_EstimatingPackage.zip"
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_FILES:
            archive.write(os.path.join(snapshot_folder, name), arcname=name)
        run_log = os.path.join(snapshot_folder, "run_log.json")
        if os.path.isfile(run_log):
            archive.write(run_log, arcname="run_log.json")
    return output_path
