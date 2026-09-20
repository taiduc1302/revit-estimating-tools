from __future__ import print_function

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "RevitEstimating.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.validation import validate_snapshot_folder, validation_passed


def main():
    parser = argparse.ArgumentParser(description="Validate a Revit estimating snapshot package.")
    parser.add_argument("folder", help="Snapshot folder containing manifest.json and raw_snapshot.json")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Print machine-readable JSON")
    args = parser.parse_args()

    findings = validate_snapshot_folder(args.folder)
    if args.json_output:
        print(json.dumps({"passed": validation_passed(findings), "findings": findings}, indent=2, sort_keys=True))
    else:
        if validation_passed(findings):
            print("PASS: snapshot package is internally consistent")
        else:
            print("FAIL: snapshot package has %s finding(s)" % len(findings))
            for item in findings:
                print("- %s: %s" % (item.get("code"), item.get("message")))
    return 0 if validation_passed(findings) else 1


if __name__ == "__main__":
    sys.exit(main())
