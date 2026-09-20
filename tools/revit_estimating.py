from __future__ import print_function

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.comparison_export import write_revision_comparison
from revit_estimating.diff import compare_snapshots
from revit_estimating.doctor import run_doctor
from revit_estimating.package import create_estimating_package
from revit_estimating.snapshot import load_raw_snapshot
from revit_estimating.validation import validate_snapshot_folder, validate_comparison_folder, validation_passed, require_valid_snapshot_input


def print_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def _report_validation(findings, label, json_output):
    passed = validation_passed(findings)
    if json_output:
        print_json({"passed": passed, "findings": findings})
    elif passed:
        print("PASS: %s is internally consistent" % label)
    else:
        print("FAIL: %s has %s finding(s)" % (label, len(findings)))
        for item in findings:
            print("- %s: %s" % (item.get("code"), item.get("message")))
    return 0 if passed else 1


def doctor_command(args):
    return _report_validation(run_doctor(args.repository), "repository/extension configuration", args.json_output)


def validate_command(args):
    return _report_validation(validate_snapshot_folder(args.folder), "snapshot package", args.json_output)


def validate_comparison_command(args):
    findings = validate_comparison_folder(args.folder, verify_inputs=not args.skip_input_files)
    return _report_validation(findings, "revision comparison package", args.json_output)


def compare_command(args):
    try:
        require_valid_snapshot_input(args.baseline, label="Baseline", allow_standalone=args.allow_standalone)
        require_valid_snapshot_input(args.current, label="Current", allow_standalone=args.allow_standalone)
        baseline = load_raw_snapshot(args.baseline)
        current = load_raw_snapshot(args.current)
        result = compare_snapshots(baseline, current)
        output_root = os.path.abspath(args.output or os.getcwd())
        if not os.path.isdir(output_root):
            os.makedirs(output_root)
        folder = write_revision_comparison(output_root, result, baseline_path=os.path.abspath(args.baseline), current_path=os.path.abspath(args.current))
    except Exception as exc:
        if args.json_output:
            print_json({"passed": False, "error": str(exc)})
        else:
            print("FAIL: %s" % exc)
        return 1
    summary = result.get("summary") or {}
    warnings = result.get("warnings") or []
    if args.json_output:
        print_json({"passed": True, "output_folder": folder, "summary": summary, "warnings": warnings})
    else:
        print("PASS: revision comparison created at %s" % folder)
        for warning in warnings:
            print("WARNING %s: %s" % (warning.get("code"), warning.get("message")))
        print("Added=%s Removed=%s Modified=%s PossibleRecreated=%s Unchanged=%s" % (
            summary.get("ADDED", 0), summary.get("REMOVED", 0), summary.get("MODIFIED", 0),
            summary.get("POSSIBLE_RECREATED", 0), summary.get("UNCHANGED", 0)))
    return 0


def package_command(args):
    try:
        path = create_estimating_package(args.folder, output_path=args.output)
    except Exception as exc:
        if args.json_output:
            print_json({"passed": False, "error": str(exc)})
        else:
            print("FAIL: %s" % exc)
        return 1
    if args.json_output:
        print_json({"passed": True, "package": os.path.abspath(path)})
    else:
        print("PASS: estimating package created at %s" % os.path.abspath(path))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Offline tools for Revit estimating snapshots.")
    commands = parser.add_subparsers(dest="command")

    doctor = commands.add_parser("doctor", help="Check repository/extension structure without Revit.")
    doctor.add_argument("repository", nargs="?", default=ROOT)
    doctor.add_argument("--json", action="store_true", dest="json_output")
    doctor.set_defaults(handler=doctor_command)

    validate = commands.add_parser("validate", help="Validate an exported snapshot package.")
    validate.add_argument("folder")
    validate.add_argument("--json", action="store_true", dest="json_output")
    validate.set_defaults(handler=validate_command)

    validate_comparison = commands.add_parser("validate-comparison", help="Validate a revision comparison package.")
    validate_comparison.add_argument("folder")
    validate_comparison.add_argument("--skip-input-files", action="store_true", help="Verify generated comparison evidence but do not require original input snapshots to remain at their recorded paths.")
    validate_comparison.add_argument("--json", action="store_true", dest="json_output")
    validate_comparison.set_defaults(handler=validate_comparison_command)

    compare = commands.add_parser("compare", help="Compare two raw_snapshot.json files.")
    compare.add_argument("baseline")
    compare.add_argument("current")
    compare.add_argument("--output")
    compare.add_argument("--allow-standalone", action="store_true", help="Allow raw snapshot JSON files that are not part of an intact exported snapshot package. Intended for fixtures/development only.")
    compare.add_argument("--json", action="store_true", dest="json_output")
    compare.set_defaults(handler=compare_command)

    package = commands.add_parser("package", help="Create a ZIP from a valid snapshot package.")
    package.add_argument("folder")
    package.add_argument("--output")
    package.add_argument("--json", action="store_true", dest="json_output")
    package.set_defaults(handler=package_command)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
