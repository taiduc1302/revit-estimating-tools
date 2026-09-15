# -*- coding: utf-8 -*-
"""Offline integrity checks for exported estimating snapshot packages."""
from __future__ import absolute_import, print_function

import os

from . import SCHEMA_VERSION
from .hashing import sha256_file
from .serialization import read_json
from .utils import to_text

REQUIRED_FILES = ("manifest.json", "raw_snapshot.json", "elements.csv", "quantities.csv", "audit_issues.csv", "summary.csv")
EVIDENCE_FILES = REQUIRED_FILES[1:]


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

    manifest_version = to_text(manifest.get("schema_version")).strip()
    snapshot_version = to_text(snapshot.get("schema_version")).strip()
    if not manifest_version:
        findings.append(finding("MANIFEST_SCHEMA_MISSING", "Manifest is missing schema_version."))
    if not snapshot_version:
        findings.append(finding("SNAPSHOT_SCHEMA_MISSING", "Raw snapshot is missing schema_version."))
    if manifest_version and snapshot_version and manifest_version != snapshot_version:
        findings.append(finding("SCHEMA_VERSION_MISMATCH", "Manifest and raw snapshot schema versions do not match.", {"manifest": manifest_version, "snapshot": snapshot_version}))
    for source, version in (("manifest", manifest_version), ("snapshot", snapshot_version)):
        if version and version != SCHEMA_VERSION:
            findings.append(finding("SCHEMA_VERSION_UNSUPPORTED", "Snapshot schema version is not supported by this tool.", {"source": source, "actual": version, "supported": SCHEMA_VERSION}))

    expected = manifest.get("evidence_hashes")
    if not isinstance(expected, dict):
        findings.append(finding("EVIDENCE_HASHES_INVALID", "Manifest evidence_hashes must be an object."))
        expected = {}
    for name in EVIDENCE_FILES:
        declared = expected.get(name)
        if not declared:
            findings.append(finding("HASH_DECLARATION_MISSING", "Manifest is missing an evidence hash.", {"file": name}))
            continue
        actual = sha256_file(os.path.join(folder, name))
        if declared != actual:
            findings.append(finding("HASH_MISMATCH", "Evidence hash does not match manifest.", {"file": name, "declared": declared, "actual": actual}))

    elements = snapshot.get("elements")
    if not isinstance(elements, list):
        findings.append(finding("ELEMENTS_INVALID", "Snapshot elements must be a list."))
        elements = []
    audit_issues = snapshot.get("audit_issues")
    if not isinstance(audit_issues, list):
        findings.append(finding("AUDIT_ISSUES_INVALID", "Snapshot audit_issues must be a list."))
        audit_issues = []

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

    for source, declared, actual, bad_code, invalid_code in (
        ("manifest", manifest.get("element_count"), len(elements), "MANIFEST_ELEMENT_COUNT_MISMATCH", "MANIFEST_ELEMENT_COUNT_INVALID"),
        ("snapshot metadata", (snapshot.get("metadata") or {}).get("element_count") if isinstance(snapshot.get("metadata") or {}, dict) else None, len(elements), "ELEMENT_COUNT_MISMATCH", "ELEMENT_COUNT_INVALID"),
        ("manifest", manifest.get("audit_issue_count"), len(audit_issues), "MANIFEST_AUDIT_COUNT_MISMATCH", "MANIFEST_AUDIT_COUNT_INVALID"),
        ("snapshot metadata", (snapshot.get("metadata") or {}).get("audit_issue_count") if isinstance(snapshot.get("metadata") or {}, dict) else None, len(audit_issues), "AUDIT_COUNT_MISMATCH", "AUDIT_COUNT_INVALID"),
    ):
        if declared is None:
            continue
        try:
            if int(declared) != actual:
                findings.append(finding(bad_code, "%s declared count does not match exported records." % source))
        except (TypeError, ValueError):
            findings.append(finding(invalid_code, "%s declared count is not an integer." % source))

    if not isinstance(snapshot.get("metadata"), dict):
        findings.append(finding("METADATA_INVALID", "Snapshot metadata must be an object."))
    return findings


def validation_passed(findings):
    return len(findings) == 0
