# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os
from .hashing import sha256_file
from .serialization import read_json

REQUIRED_FILES = ("manifest.json", "raw_snapshot.json", "elements.csv", "quantities.csv", "audit_issues.csv", "summary.csv")


def finding(code, message, values=None):
    return {"code": code, "message": message, "values": values or {}}


def validate_snapshot_folder(folder):
    findings = []
    for name in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(folder, name)):
            findings.append(finding("FILE_MISSING", "Required snapshot file is missing.", {"file": name}))
    if findings:
        return findings

    manifest = read_json(os.path.join(folder, "manifest.json"))
    snapshot = read_json(os.path.join(folder, "raw_snapshot.json"))
    expected = manifest.get("evidence_hashes") or {}
    for name in REQUIRED_FILES[1:]:
        actual = sha256_file(os.path.join(folder, name))
        if expected.get(name) != actual:
            findings.append(finding("HASH_MISMATCH", "Evidence hash does not match manifest.", {"file": name}))

    elements = snapshot.get("elements")
    if not isinstance(elements, list):
        findings.append(finding("ELEMENTS_INVALID", "Snapshot elements must be a list."))
        return findings

    seen = set()
    for index, element in enumerate(elements):
        key = element.get("element_key") if isinstance(element, dict) else None
        if not key:
            findings.append(finding("ELEMENT_KEY_MISSING", "Element record is missing element_key.", {"index": index}))
        elif key in seen:
            findings.append(finding("ELEMENT_KEY_DUPLICATE", "Duplicate element_key found.", {"element_key": key}))
        else:
            seen.add(key)

    metadata = snapshot.get("metadata") or {}
    if metadata.get("element_count") is not None and int(metadata.get("element_count")) != len(elements):
        findings.append(finding("ELEMENT_COUNT_MISMATCH", "Declared element_count does not match exported records."))
    return findings


def validation_passed(findings):
    return len(findings) == 0
