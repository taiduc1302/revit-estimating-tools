# -*- coding: utf-8 -*-
"""Offline integrity checks for snapshot and revision-comparison packages."""
from __future__ import absolute_import, print_function

import os

from . import SCHEMA_VERSION
from .hashing import sha256_file
from .serialization import read_json, read_text
from .evidence import snapshot_csv_texts, comparison_csv_texts
from .diff import compare_snapshots
from .utils import to_text

REQUIRED_FILES = ("manifest.json", "raw_snapshot.json", "elements.csv", "quantities.csv", "audit_issues.csv", "summary.csv")
EVIDENCE_FILES = REQUIRED_FILES[1:]
OPTIONAL_EVIDENCE_FILES = ("run_log.json",)
COMPARISON_REQUIRED_FILES = ("comparison_manifest.json", "revision_diff.json", "quantity_deltas.csv", "element_changes.csv")
COMPARISON_EVIDENCE_FILES = COMPARISON_REQUIRED_FILES[1:]
EXPECTED_STATUS = "NOT_ESTIMATOR_VALIDATED"
EXPECTED_TOOL = "Revit Estimating Tools"


def finding(code, message, values=None):
    return {"code": code, "message": message, "values": values or {}}


def _read_json_object(path, code, findings):
    try:
        data = read_json(path)
    except Exception as exc:
        findings.append(finding(code, "JSON file could not be parsed.", {"file": os.path.basename(path), "error": to_text(exc)}))
        return None
    if not isinstance(data, dict):
        findings.append(finding(code, "JSON root must be an object.", {"file": os.path.basename(path)}))
        return None
    return data


def _validate_schema_value(version, source, findings):
    value = to_text(version).strip()
    if not value:
        findings.append(finding("SCHEMA_VERSION_MISSING", "%s is missing schema_version." % source))
    elif value != SCHEMA_VERSION:
        findings.append(finding("SCHEMA_VERSION_UNSUPPORTED", "Schema version is not supported by this tool.", {"source": source, "actual": value, "supported": SCHEMA_VERSION}))
    return value


def _valid_sha256(value):
    text = to_text(value).strip().lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _validate_category_config_provenance(manifest, snapshot, findings):
    extraction = manifest.get("extraction_config")
    if not isinstance(extraction, dict):
        findings.append(finding("EXTRACTION_CONFIG_INVALID", "Manifest extraction_config must be an object."))
        return
    categories = extraction.get("categories")
    if not isinstance(categories, dict):
        findings.append(finding("CATEGORY_CONFIG_EVIDENCE_MISSING", "Manifest must record category configuration provenance."))
        return

    required = ("path", "sha256", "schema_version", "category_count", "mode")
    missing = [name for name in required if categories.get(name) in (None, "")]
    if missing:
        findings.append(finding("CATEGORY_CONFIG_EVIDENCE_INCOMPLETE", "Category configuration provenance is incomplete.", {"missing": missing}))
    if categories.get("mode") != "REQUIRED_FAIL_CLOSED":
        findings.append(finding("CATEGORY_CONFIG_MODE_INVALID", "Category configuration must be recorded as fail-closed.", {"mode": categories.get("mode")}))
    if not _valid_sha256(categories.get("sha256")):
        findings.append(finding("CATEGORY_CONFIG_HASH_INVALID", "Category configuration SHA-256 is missing or malformed."))
    try:
        if int(categories.get("category_count")) <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        findings.append(finding("CATEGORY_CONFIG_COUNT_INVALID", "Category configuration category_count must be a positive integer."))

    metadata = snapshot.get("metadata")
    if isinstance(metadata, dict) and metadata.get("extraction_config") != extraction:
        findings.append(finding("EXTRACTION_CONFIG_MISMATCH", "Raw snapshot extraction_config does not match manifest extraction_config."))


def _validate_snapshot_manifest_contract(manifest, snapshot, findings):
    manifest_status = to_text(manifest.get("status")).strip()
    if manifest_status != EXPECTED_STATUS:
        findings.append(finding("STATUS_INVALID", "Snapshot manifest status must remain NOT_ESTIMATOR_VALIDATED.", {"actual": manifest_status}))
    if to_text(manifest.get("tool")).strip() != EXPECTED_TOOL:
        findings.append(finding("TOOL_IDENTITY_INVALID", "Snapshot manifest tool identity is unexpected.", {"actual": manifest.get("tool")}))

    metadata = snapshot.get("metadata")
    if not isinstance(metadata, dict):
        return
    metadata_status = to_text(metadata.get("status")).strip()
    if metadata_status != EXPECTED_STATUS:
        findings.append(finding("SNAPSHOT_STATUS_INVALID", "Raw snapshot metadata status must remain NOT_ESTIMATOR_VALIDATED.", {"actual": metadata_status}))

    mirrored_fields = (
        "tool", "tool_version", "status", "created_at", "project_name", "model",
        "element_count", "audit_issue_count", "extraction_config",
    )
    mismatched = [name for name in mirrored_fields if manifest.get(name) != metadata.get(name)]
    if mismatched:
        findings.append(finding(
            "MANIFEST_METADATA_MISMATCH",
            "Manifest metadata does not match the hashed raw snapshot metadata.",
            {"fields": mismatched},
        ))


def _validate_comparison_manifest_contract(manifest, findings):
    status = to_text(manifest.get("status")).strip()
    if status != EXPECTED_STATUS:
        findings.append(finding("COMPARISON_STATUS_INVALID", "Comparison manifest status must remain NOT_ESTIMATOR_VALIDATED.", {"actual": status}))
    if to_text(manifest.get("tool")).strip() != EXPECTED_TOOL:
        findings.append(finding("COMPARISON_TOOL_IDENTITY_INVALID", "Comparison manifest tool identity is unexpected.", {"actual": manifest.get("tool")}))


def _validate_declared_hashes(folder, names, expected, findings):
    if not isinstance(expected, dict):
        findings.append(finding("EVIDENCE_HASHES_INVALID", "Manifest evidence_hashes must be an object."))
        expected = {}
    for name in names:
        declared = expected.get(name)
        if not declared:
            findings.append(finding("HASH_DECLARATION_MISSING", "Manifest is missing an evidence hash.", {"file": name}))
            continue
        path = os.path.join(folder, name)
        actual = sha256_file(path)
        if declared != actual:
            findings.append(finding("HASH_MISMATCH", "Evidence hash does not match manifest.", {"file": name, "declared": declared, "actual": actual}))
    return expected


def _validate_optional_hashes(folder, names, expected, findings):
    if not isinstance(expected, dict):
        expected = {}
    for name in names:
        path = os.path.join(folder, name)
        exists = os.path.isfile(path)
        declared = expected.get(name)
        if exists and not declared:
            findings.append(finding("HASH_DECLARATION_MISSING", "Optional evidence file exists but is not hashed in the manifest.", {"file": name}))
        elif not exists and declared:
            findings.append(finding("FILE_MISSING", "Manifest declares an optional evidence file that is missing.", {"file": name}))
        elif exists and declared:
            actual = sha256_file(path)
            if declared != actual:
                findings.append(finding("HASH_MISMATCH", "Evidence hash does not match manifest.", {"file": name, "declared": declared, "actual": actual}))


def _validate_derived_evidence(folder, expected_texts, findings):
    for name in sorted(expected_texts.keys()):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            actual = read_text(path)
        except Exception as exc:
            findings.append(finding("DERIVED_EVIDENCE_READ_FAILED", "Derived evidence file could not be read.", {"file": name, "error": to_text(exc)}))
            continue
        if actual != expected_texts[name]:
            findings.append(finding(
                "DERIVED_EVIDENCE_MISMATCH",
                "Derived evidence does not match its authoritative JSON source.",
                {"file": name},
            ))


def _validate_comparison_recomputation(manifest, result, findings):
    baseline = manifest.get("baseline_snapshot") or {}
    current = manifest.get("current_snapshot") or {}
    baseline_path = to_text(baseline.get("path")).strip()
    current_path = to_text(current.get("path")).strip()
    if not baseline_path or not current_path:
        return
    if not os.path.isfile(baseline_path) or not os.path.isfile(current_path):
        return
    try:
        baseline_snapshot = read_json(baseline_path)
        current_snapshot = read_json(current_path)
        recomputed = compare_snapshots(baseline_snapshot, current_snapshot)
    except Exception as exc:
        findings.append(finding(
            "COMPARISON_RECOMPUTATION_FAILED",
            "Revision comparison could not be recomputed from the recorded inputs.",
            {"error": to_text(exc)},
        ))
        return
    if recomputed != result:
        findings.append(finding(
            "COMPARISON_RECOMPUTATION_MISMATCH",
            "revision_diff.json does not match a fresh comparison of the recorded input snapshots.",
        ))


def snapshot_input_package_status(path):
    absolute = os.path.abspath(path)
    if not os.path.isfile(absolute):
        return "FILE_NOT_FOUND"
    folder = os.path.dirname(absolute)
    expected_raw = os.path.join(folder, "raw_snapshot.json")
    if os.path.normcase(absolute) != os.path.normcase(expected_raw):
        return "STANDALONE_UNVERIFIED"

    sibling_names = [name for name in REQUIRED_FILES if name != "raw_snapshot.json"]
    if not any(os.path.exists(os.path.join(folder, name)) for name in sibling_names):
        return "STANDALONE_UNVERIFIED"
    return "VALID_PACKAGE" if validation_passed(validate_snapshot_folder(folder)) else "INVALID_PACKAGE"


def validate_snapshot_input_file(path, allow_standalone=False):
    absolute = os.path.abspath(path)
    if not os.path.isfile(absolute):
        return [finding("SNAPSHOT_INPUT_MISSING", "Snapshot input file does not exist.", {"path": absolute})]

    status = snapshot_input_package_status(absolute)
    if status == "VALID_PACKAGE":
        return []
    if status == "INVALID_PACKAGE":
        return validate_snapshot_folder(os.path.dirname(absolute))
    if allow_standalone:
        return []
    return [finding(
        "SNAPSHOT_PACKAGE_REQUIRED",
        "Snapshot comparison requires raw_snapshot.json from an intact validated snapshot package.",
        {"path": absolute, "status": status},
    )]


def require_valid_snapshot_input(path, label="Snapshot", allow_standalone=False):
    findings = validate_snapshot_input_file(path, allow_standalone=allow_standalone)
    if findings:
        codes = ", ".join(sorted(set(item.get("code", "SNAPSHOT_INPUT_INVALID") for item in findings)))
        raise ValueError("%s input failed snapshot package validation: %s" % (label, codes))
    return True


def validate_snapshot_folder(folder):
    findings = []
    if not os.path.isdir(folder):
        return [finding("FOLDER_MISSING", "Snapshot folder does not exist.", {"folder": folder})]

    for name in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(folder, name)):
            findings.append(finding("FILE_MISSING", "Required snapshot file is missing.", {"file": name}))
    if findings:
        return findings

    manifest = _read_json_object(os.path.join(folder, "manifest.json"), "MANIFEST_INVALID", findings)
    snapshot = _read_json_object(os.path.join(folder, "raw_snapshot.json"), "SNAPSHOT_INVALID", findings)
    if manifest is None or snapshot is None:
        return findings

    manifest_version = _validate_schema_value(manifest.get("schema_version"), "manifest", findings)
    snapshot_version = _validate_schema_value(snapshot.get("schema_version"), "raw snapshot", findings)
    if manifest_version and snapshot_version and manifest_version != snapshot_version:
        findings.append(finding("SCHEMA_VERSION_MISMATCH", "Manifest and raw snapshot schema versions do not match.", {"manifest": manifest_version, "snapshot": snapshot_version}))

    _validate_snapshot_manifest_contract(manifest, snapshot, findings)
    _validate_category_config_provenance(manifest, snapshot, findings)
    expected_hashes = _validate_declared_hashes(folder, EVIDENCE_FILES, manifest.get("evidence_hashes"), findings)
    _validate_optional_hashes(folder, OPTIONAL_EVIDENCE_FILES, expected_hashes, findings)

    elements = snapshot.get("elements")
    elements_valid = isinstance(elements, list)
    if not elements_valid:
        findings.append(finding("ELEMENTS_INVALID", "Snapshot elements must be a list."))
        elements = []
    audit_issues = snapshot.get("audit_issues")
    audit_issues_valid = isinstance(audit_issues, list)
    if not audit_issues_valid:
        findings.append(finding("AUDIT_ISSUES_INVALID", "Snapshot audit_issues must be a list."))
        audit_issues = []

    if elements_valid and audit_issues_valid:
        _validate_derived_evidence(folder, snapshot_csv_texts(snapshot), findings)

    seen = set()
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            findings.append(finding("ELEMENT_INVALID", "Element record must be an object.", {"index": index}))
            continue
        key = to_text(element.get("element_key")).strip()
        if not key:
            findings.append(finding("ELEMENT_KEY_MISSING", "Element record is missing element_key.", {"index": index}))
        elif key in seen:
            findings.append(finding("ELEMENT_KEY_DUPLICATE", "Duplicate element_key found.", {"element_key": key}))
        else:
            seen.add(key)
        if not to_text(element.get("source_scope_key")).strip():
            findings.append(finding("SOURCE_SCOPE_KEY_MISSING", "Element record is missing source_scope_key required for stable revision comparison.", {"index": index, "element_key": key}))

    metadata = snapshot.get("metadata")
    if not isinstance(metadata, dict):
        findings.append(finding("METADATA_INVALID", "Snapshot metadata must be an object."))
        metadata = {}

    for source, declared, actual, bad_code, invalid_code in (
        ("manifest", manifest.get("element_count"), len(elements), "MANIFEST_ELEMENT_COUNT_MISMATCH", "MANIFEST_ELEMENT_COUNT_INVALID"),
        ("snapshot metadata", metadata.get("element_count"), len(elements), "ELEMENT_COUNT_MISMATCH", "ELEMENT_COUNT_INVALID"),
        ("manifest", manifest.get("audit_issue_count"), len(audit_issues), "MANIFEST_AUDIT_COUNT_MISMATCH", "MANIFEST_AUDIT_COUNT_INVALID"),
        ("snapshot metadata", metadata.get("audit_issue_count"), len(audit_issues), "AUDIT_COUNT_MISMATCH", "AUDIT_COUNT_INVALID"),
    ):
        if declared is None:
            continue
        try:
            if int(declared) != actual:
                findings.append(finding(bad_code, "%s declared count does not match exported records." % source))
        except (TypeError, ValueError):
            findings.append(finding(invalid_code, "%s declared count is not an integer." % source))
    return findings


def _validate_input_snapshot_evidence(item, label, findings, verify_file=True):
    if not isinstance(item, dict):
        findings.append(finding("COMPARISON_INPUT_INVALID", "%s snapshot evidence must be an object." % label))
        return
    path = to_text(item.get("path")).strip()
    declared = to_text(item.get("sha256")).strip()
    status = to_text(item.get("status")).strip()
    if status != "HASHED":
        findings.append(finding("COMPARISON_INPUT_NOT_HASHED", "%s snapshot was not recorded as hashed." % label, {"status": status}))
    if not path:
        findings.append(finding("COMPARISON_INPUT_PATH_MISSING", "%s snapshot evidence is missing its recorded path." % label))
    if not _valid_sha256(declared):
        findings.append(finding("COMPARISON_INPUT_HASH_INVALID", "%s snapshot SHA-256 is missing or malformed." % label, {"sha256": declared}))

    package_status = to_text(item.get("package_status")).strip()
    if package_status not in ("VALID_PACKAGE", "STANDALONE_UNVERIFIED"):
        findings.append(finding("COMPARISON_INPUT_PACKAGE_STATUS_INVALID", "%s snapshot package status is invalid." % label, {"status": package_status}))

    if not verify_file:
        return
    if not path or not os.path.isfile(path):
        findings.append(finding("COMPARISON_INPUT_MISSING", "%s snapshot file is no longer available at the recorded path." % label, {"path": path}))
        return
    actual = sha256_file(path)
    if not declared or declared != actual:
        findings.append(finding("COMPARISON_INPUT_HASH_MISMATCH", "%s snapshot no longer matches the comparison manifest." % label, {"path": path, "declared": declared, "actual": actual}))

    if package_status == "VALID_PACKAGE":
        package_findings = validate_snapshot_folder(os.path.dirname(path))
        if package_findings:
            findings.append(finding(
                "COMPARISON_INPUT_PACKAGE_INVALID",
                "%s source snapshot package no longer passes integrity validation." % label,
                {"codes": sorted(set(entry.get("code") for entry in package_findings))},
            ))


def validate_comparison_folder(folder, verify_inputs=True):
    findings = []
    if not os.path.isdir(folder):
        return [finding("FOLDER_MISSING", "Comparison folder does not exist.", {"folder": folder})]
    for name in COMPARISON_REQUIRED_FILES:
        if not os.path.isfile(os.path.join(folder, name)):
            findings.append(finding("FILE_MISSING", "Required comparison file is missing.", {"file": name}))
    if findings:
        return findings

    manifest = _read_json_object(os.path.join(folder, "comparison_manifest.json"), "COMPARISON_MANIFEST_INVALID", findings)
    result = _read_json_object(os.path.join(folder, "revision_diff.json"), "REVISION_DIFF_INVALID", findings)
    if manifest is None or result is None:
        return findings

    manifest_version = _validate_schema_value(manifest.get("schema_version"), "comparison manifest", findings)
    result_version = _validate_schema_value(result.get("schema_version"), "revision diff", findings)
    if manifest_version and result_version and manifest_version != result_version:
        findings.append(finding("SCHEMA_VERSION_MISMATCH", "Comparison manifest and revision diff schema versions do not match.", {"manifest": manifest_version, "revision_diff": result_version}))

    _validate_comparison_manifest_contract(manifest, findings)
    _validate_declared_hashes(folder, COMPARISON_EVIDENCE_FILES, manifest.get("evidence_hashes"), findings)
    _validate_derived_evidence(folder, comparison_csv_texts(result), findings)

    manifest_summary = manifest.get("summary")
    result_summary = result.get("summary")
    if not isinstance(manifest_summary, dict) or not isinstance(result_summary, dict):
        findings.append(finding("COMPARISON_SUMMARY_INVALID", "Comparison summaries must be objects."))
    elif manifest_summary != result_summary:
        findings.append(finding("COMPARISON_SUMMARY_MISMATCH", "Comparison manifest summary does not match revision_diff.json."))

    _validate_input_snapshot_evidence(manifest.get("baseline_snapshot"), "Baseline", findings, verify_file=verify_inputs)
    _validate_input_snapshot_evidence(manifest.get("current_snapshot"), "Current", findings, verify_file=verify_inputs)
    if verify_inputs:
        _validate_comparison_recomputation(manifest, result, findings)
    return findings


def validation_passed(findings):
    return len(findings) == 0
