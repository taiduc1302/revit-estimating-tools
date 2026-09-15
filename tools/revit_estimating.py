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
from revit_estimating.package import create_estimating_package
from revit_estimating.snapshot import load_raw_snapshot
from revit_estimating.validation import validate_snapshot_folder, validation_passed


def print_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def validate_command(args):
    findings = validate_snapshot_folder(args.folder)
    passed = validation_passed(findings)
    if args.json_output:
        print_json({"passed": passed, "findings": findings})
    elif passed:
        print("PASS: snapshot package is internally consistent")
    else:
        print("FAIL: snapshot package has %s finding(s)" % len(findings))
        for item in findings:
            print("- %s: %s" % (item.get("code"), item.get("message")))
    return 0 if passed else 1


def compare_command(args):
    try:
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
    if args.json_output:
        print_json({"passed": True, "output_folder": folder, "summary": summary})
    else:
        print("PASS: revision comparison created at %s" % folder)
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

    validate = commands.add_parser("validate")
    validate.add_argument("folder")
    validate.add_argument("--json", action="store_true", dest="json_output")
    validate.set_defaults(handler=validate_command)

    compare = commands.add_parser("compare")
    compare.add_argument("baseline")
    compare.add_argument("current")
    compare.add_argument("--output")
    compare.add_argument("--json", action="store_true", dest="json_output")
    compare.set_defaults(handler=compare_command)

    package = commands.add_parser("package")
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
