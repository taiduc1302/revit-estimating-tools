# -*- coding: utf-8 -*-
from __future__ import print_function

from pyrevit import forms, revit, script

from revit_estimating import __version__
from revit_estimating.audit import audit_model
from revit_estimating.logging_utils import build_run_record, write_run_log
from revit_estimating.manifest import build_manifest, utc_now_iso
from revit_estimating.revit_adapter import extract_model
from revit_estimating.snapshot import write_snapshot_package

output = script.get_output()
output.close_others()

output_root = forms.pick_folder(title="Choose estimating snapshot output folder")
if not output_root:
    script.exit()

started_at = utc_now_iso()
try:
    result = extract_model(revit.doc, getattr(revit.doc, "Application", None))
    issues = audit_model(result["elements"], result["link_issues"])
    metadata = result["model_metadata"]
    project_name = metadata.get("project_name") or metadata.get("host_document") or "Model"

    manifest = build_manifest(
        project_name=project_name,
        model_metadata=metadata,
        element_count=len(result["elements"]),
        audit_count=len(issues),
        extraction_config={"categories": result.get("category_config") or {}, "read_only": True},
        created_at=started_at,
    )
    folder = write_snapshot_package(output_root, manifest, result["elements"], issues)
    write_run_log(folder, build_run_record(
        "Extract Snapshot", metadata.get("host_document"), started_at,
        element_count=len(result["elements"]), warning_count=len(issues), export_path=folder, tool_version=__version__
    ))
except Exception as exc:
    forms.alert(str(exc), title="Extract Snapshot", warn_icon=True)
    script.exit()

output.print_md("# Estimating Snapshot Created")
output.print_md("**Folder:** `%s`  " % folder)
output.print_md("**Elements:** %s  " % len(result["elements"]))
output.print_md("**Audit issues:** %s  " % len(issues))
config_evidence = result.get("category_config") or {}
if config_evidence.get("sha256"):
    output.print_md("**Category config SHA-256:** `%s`  " % config_evidence.get("sha256"))
if result.get("skipped_categories"):
    output.print_md("**Skipped categories due to extraction errors:** %s  " % len(result.get("skipped_categories") or []))
output.print_md("**Status:** `NOT_ESTIMATOR_VALIDATED`")
