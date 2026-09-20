from __future__ import print_function

import argparse
import json
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "RevitEstimating.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.comparison_export import write_revision_comparison
from revit_estimating.diff import compare_snapshots
from revit_estimating.hashing import sha256_file
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


def _benchmark_element(index, key_prefix="u", length=10.0):
    uid = "%s-%s" % (key_prefix, index)
    return {
        "element_key": "HOST:%s" % uid,
        "source_scope_key": "HOST",
        "source_document": "Synthetic.rvt",
        "unique_id": uid,
        "category": "Pipes",
        "family": "Pipe",
        "type": "PVC 300",
        "system": "Storm",
        "material": "PVC",
        "level": "Level 1",
        "mark": "",
        "size": {"diameter_mm": 300.0},
        "location": {"x_m": float(index), "y_m": 0.0, "z_m": 0.0},
        "quantities": {"length_m": float(length)},
        "primary_quantity_type": "LENGTH",
        "primary_quantity_value": float(length),
        "primary_quantity_unit": "M",
        "quantity_aggregation_excluded": False,
        "parameters": {},
    }


def benchmark_command(args):
    count = max(1, int(args.elements))
    replacements = max(0, min(int(args.replacements), count))
    stable = count - replacements
    baseline_elements = []
    current_elements = []
    for index in range(stable):
        baseline_elements.append(_benchmark_element(index, "stable", 10.0))
        current_elements.append(_benchmark_element(index, "stable", 10.0))
    for index in range(replacements):
        baseline_elements.append(_benchmark_element(stable + index, "old", 10.0))
        current_elements.append(_benchmark_element(stable + index, "new", 10.0))

    baseline = {"schema_version": "0.1", "metadata": {"model": {"project_name": "Synthetic"}}, "elements": baseline_elements, "audit_issues": []}
    current = {"schema_version": "0.1", "metadata": {"model": {"project_name": "Synthetic"}}, "elements": current_elements, "audit_issues": []}

    started = time.time()
    result = compare_snapshots(baseline, current)
    elapsed = max(time.time() - started, 0.000001)
    payload = {
        "passed": True,
        "elements_per_snapshot": count,
        "replacements": replacements,
        "elapsed_seconds": round(elapsed, 4),
        "elements_per_second": round((count * 2.0) / elapsed, 2),
        "summary": result.get("summary") or {},
        "warnings": result.get("warnings") or [],
    }
    max_seconds = args.max_seconds
    if max_seconds is not None and elapsed > float(max_seconds):
        payload["passed"] = False
        payload["error"] = "Benchmark exceeded max seconds: %.4f > %.4f" % (elapsed, float(max_seconds))

    if args.json_output:
        print_json(payload)
    else:
        print("PASS" if payload["passed"] else "FAIL")
        print("Elements/snapshot=%s replacements=%s elapsed=%.4fs throughput=%.2f elements/s" % (
            count, replacements, elapsed, payload["elements_per_second"]))
        for warning in payload["warnings"]:
            print("WARNING %s: %s" % (warning.get("code"), warning.get("message")))
    return 0 if payload["passed"] else 1


def _extension_files(extension_root):
    files = []
    for dirpath, dirnames, filenames in os.walk(extension_root):
        dirnames[:] = sorted([name for name in dirnames if name != "__pycache__"])
        for filename in sorted(filenames):
            if filename.endswith((".pyc", ".pyo")) or filename == ".DS_Store":
                continue
            path = os.path.join(dirpath, filename)
            relative = os.path.relpath(path, extension_root)
            files.append((relative, path))
    return sorted(files, key=lambda item: item[0].replace(os.sep, "/"))


def build_extension_command(args):
    findings = run_doctor(ROOT)
    if findings:
        return _report_validation(findings, "repository/extension configuration", args.json_output)

    extension_root = os.path.join(ROOT, "RevitEstimating.extension")
    output_path = os.path.abspath(args.output or os.path.join(ROOT, "dist", "RevitEstimating.extension.zip"))
    extension_abs = os.path.normcase(os.path.abspath(extension_root))
    output_abs = os.path.normcase(output_path)
    if output_abs == extension_abs or output_abs.startswith(extension_abs + os.sep):
        message = "Extension ZIP output must be outside RevitEstimating.extension."
        if args.json_output:
            print_json({"passed": False, "error": message})
        else:
            print("FAIL: %s" % message)
        return 1

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    files = _extension_files(extension_root)
    required = set([
        "extension.json",
        os.path.join("lib", "revit_estimating", "__init__.py"),
        os.path.join("config", "categories.json"),
    ])
    available = set(relative for relative, _ in files)
    missing = sorted(required - available)
    if missing:
        message = "Extension build is missing required files: %s" % ", ".join(missing)
        if args.json_output:
            print_json({"passed": False, "error": message})
        else:
            print("FAIL: %s" % message)
        return 1

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, source in files:
            arcname = ("RevitEstimating.extension/" + relative.replace(os.sep, "/"))
            with open(source, "rb") as stream:
                data = stream.read()
            info = zipfile.ZipInfo(arcname, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)

    payload = {
        "passed": True,
        "package": output_path,
        "sha256": sha256_file(output_path),
        "file_count": len(files),
    }
    if args.json_output:
        print_json(payload)
    else:
        print("PASS: extension package created at %s" % output_path)
        print("SHA-256: %s" % payload["sha256"])
        print("Files: %s" % payload["file_count"])
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
    doctor.add_argument("repository", nargs="?", default=ROOT, help="Repository root or standalone RevitEstimating.extension folder.")
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

    build_extension = commands.add_parser("build-extension", help="Build a deterministic self-contained RevitEstimating.extension ZIP.")
    build_extension.add_argument("--output", help="Output ZIP path. Defaults to dist/RevitEstimating.extension.zip.")
    build_extension.add_argument("--json", action="store_true", dest="json_output")
    build_extension.set_defaults(handler=build_extension_command)

    benchmark = commands.add_parser("benchmark", help="Run a synthetic offline revision-comparison benchmark.")
    benchmark.add_argument("--elements", type=int, default=20000, help="Elements per synthetic snapshot.")
    benchmark.add_argument("--replacements", type=int, default=600, help="Elements recreated with new identities.")
    benchmark.add_argument("--max-seconds", type=float, default=None, help="Return failure if runtime exceeds this limit.")
    benchmark.add_argument("--json", action="store_true", dest="json_output")
    benchmark.set_defaults(handler=benchmark_command)

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
