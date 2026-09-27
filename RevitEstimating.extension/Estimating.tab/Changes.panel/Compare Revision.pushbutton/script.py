# -*- coding: utf-8 -*-
from __future__ import print_function

from pyrevit import forms, script

from revit_estimating.comparison_export import write_revision_comparison
from revit_estimating.diff import compare_snapshots
from revit_estimating.snapshot import load_raw_snapshot
from revit_estimating.validation import require_valid_snapshot_input

output = script.get_output()
output.close_others()

baseline_path = forms.pick_file(file_ext="json", title="Select BASELINE raw_snapshot.json")
if not baseline_path:
    script.exit()
current_path = forms.pick_file(file_ext="json", title="Select CURRENT raw_snapshot.json")
if not current_path:
    script.exit()
output_root = forms.pick_folder(title="Choose revision comparison output folder")
if not output_root:
    script.exit()

try:
    require_valid_snapshot_input(baseline_path, label="Baseline")
    require_valid_snapshot_input(current_path, label="Current")
    baseline = load_raw_snapshot(baseline_path)
    current = load_raw_snapshot(current_path)
    result = compare_snapshots(baseline, current)
    folder = write_revision_comparison(output_root, result, baseline_path=baseline_path, current_path=current_path)
except Exception as exc:
    forms.alert(str(exc), title="Compare Revision", warn_icon=True)
    script.exit()

summary = result["summary"]

output.print_md("# Revision Comparison")
for warning in result.get("warnings") or []:
    output.print_md("**WARNING — %s:** %s  " % (warning.get("code"), warning.get("message")))
output.print_md("**Added:** %s · **Removed:** %s · **Modified:** %s · **Possible recreated:** %s · **Unchanged:** %s" % (
    summary.get("ADDED", 0), summary.get("REMOVED", 0), summary.get("MODIFIED", 0),
    summary.get("POSSIBLE_RECREATED", 0), summary.get("UNCHANGED", 0)
))
rows = []
for delta in result.get("quantity_deltas") or []:
    if delta.get("delta"):
        rows.append([
            delta.get("source_document"), delta.get("category"), delta.get("type"), delta.get("system"),
            delta.get("material"), delta.get("size"), delta.get("baseline_quantity"),
            delta.get("current_quantity"), delta.get("delta"), delta.get("unit")
        ])
if rows:
    output.print_table(rows, columns=["Source", "Category", "Type", "System", "Material", "Size", "Before", "After", "Delta", "Unit"])
output.print_md("\n**Comparison package:** `%s`" % folder)
output.print_md("\n> `POSSIBLE_RECREATED` is an inferred match and must be reviewed by an estimator.")
