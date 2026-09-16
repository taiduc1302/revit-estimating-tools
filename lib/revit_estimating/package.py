# -*- coding: utf-8 -*-
"""Create a portable ZIP from a consistent snapshot folder."""
from __future__ import absolute_import, print_function

import os
import zipfile

from .validation import REQUIRED_FILES, validate_snapshot_folder, validation_passed


def create_estimating_package(snapshot_folder, output_path=None):
    findings = validate_snapshot_folder(snapshot_folder)
    if not validation_passed(findings):
        codes = ", ".join(sorted(set(item.get("code", "VALIDATION_ERROR") for item in findings)))
        raise ValueError("Snapshot package failed integrity validation: %s" % codes)
    if output_path is None:
        output_path = snapshot_folder.rstrip("\\/") + "_EstimatingPackage.zip"
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_FILES:
            archive.write(os.path.join(snapshot_folder, name), arcname=name)
        run_log = os.path.join(snapshot_folder, "run_log.json")
        if os.path.isfile(run_log):
            archive.write(run_log, arcname="run_log.json")
    return output_path
