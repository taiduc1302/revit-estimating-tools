# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys

from pyrevit import forms, revit, script

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LIB = os.path.join(ROOT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.audit import audit_model, audit_summary
from revit_estimating.revit_adapter import extract_model

output = script.get_output()
output.close_others()

try:
    result = extract_model(revit.doc, getattr(revit.doc, "Application", None))
    issues = audit_model(result["elements"], result["link_issues"])
    summary = audit_summary(issues)
except Exception as exc:
    forms.alert(str(exc), title="Model Audit", warn_icon=True)
    script.exit()

output.print_md("# Estimating Model Audit")
output.print_md("**Model:** %s  " % result["model_metadata"].get("host_document"))
output.print_md("**Elements reviewed:** %s  " % len(result["elements"]))
output.print_md("**Issues:** %s high · %s medium · %s low · %s info" % (
    summary.get("HIGH", 0), summary.get("MEDIUM", 0), summary.get("LOW", 0), summary.get("INFO", 0)
))
if result.get("skipped_categories"):
    output.print_md("**Skipped categories due to extraction errors:** %s  " % len(result.get("skipped_categories") or []))

if not issues:
    output.print_md("\nNo estimating audit issues were found by the current rules.")
else:
    rows = []
    for issue in issues:
        rows.append([
            issue.get("severity"), issue.get("rule_id"), issue.get("source_document"),
            issue.get("category") or "", issue.get("element_id") or "", issue.get("message")
        ])
    output.print_table(rows, columns=["Severity", "Rule", "Source", "Category", "Element ID", "Message"])

output.print_md("\n> This audit is advisory. It does not certify model completeness or estimating suitability.")
