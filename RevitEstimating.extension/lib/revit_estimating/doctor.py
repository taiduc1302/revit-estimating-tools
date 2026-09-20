# -*- coding: utf-8 -*-
"""Dependency-free repository/install self-checks that do not require Revit."""
from __future__ import absolute_import, print_function

import io
import json
import os

from . import SCHEMA_VERSION
from .validation import finding, validation_passed

EXPECTED_BUTTONS = (
    os.path.join("Estimating.tab", "Model.panel", "Model Audit.pushbutton"),
    os.path.join("Estimating.tab", "Model.panel", "Extract Snapshot.pushbutton"),
    os.path.join("Estimating.tab", "Changes.panel", "Compare Revision.pushbutton"),
    os.path.join("Estimating.tab", "Export.panel", "Estimating Package.pushbutton"),
)
MODEL_BUTTONS = set(EXPECTED_BUTTONS[:2])
ALLOWED_PRIMARY_QUANTITIES = set(("LENGTH", "AREA", "VOLUME", "COUNT"))


def _read_text(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return stream.read()


def _read_json(path, code, findings):
    try:
        data = json.loads(_read_text(path))
    except Exception as exc:
        findings.append(finding(code, "JSON file could not be parsed.", {"path": path, "error": str(exc)}))
        return None
    return data


def _resolve_target(target):
    absolute = os.path.abspath(target)
    basename = os.path.basename(absolute).lower()
    if basename.endswith(".extension"):
        return None, absolute
    if os.path.isdir(absolute) and os.path.isfile(os.path.join(absolute, "extension.json")):
        return None, absolute
    return absolute, os.path.join(absolute, "RevitEstimating.extension")


def run_doctor(target):
    """Validate a repository checkout or standalone .extension folder without Revit."""
    findings = []
    repository_root, extension = _resolve_target(target)
    root = repository_root or os.path.dirname(extension)
    manifest_path = os.path.join(extension, "extension.json")
    runtime_lib = os.path.join(extension, "lib", "revit_estimating")
    categories_path = os.path.join(extension, "config", "categories.json")
    schemas = ()
    if repository_root is not None:
        schemas = (
            os.path.join(repository_root, "schemas", "manifest.schema.json"),
            os.path.join(repository_root, "schemas", "snapshot.schema.json"),
        )

    if not os.path.isdir(extension):
        findings.append(finding("EXTENSION_FOLDER_MISSING", "RevitEstimating.extension folder is missing."))
        return findings

    if not os.path.basename(extension).lower().endswith(".extension"):
        findings.append(finding("EXTENSION_SUFFIX_INVALID", "pyRevit UI extension folder must end with .extension.", {"folder": os.path.basename(extension)}))

    if not os.path.isfile(os.path.join(runtime_lib, "__init__.py")):
        findings.append(finding("EXTENSION_RUNTIME_MISSING", "Self-contained extension runtime lib/revit_estimating is missing."))
    if repository_root is not None:
        if os.path.isdir(os.path.join(repository_root, "lib", "revit_estimating")) or os.path.isfile(os.path.join(repository_root, "config", "categories.json")):
            findings.append(finding("LEGACY_RUNTIME_DUPLICATE", "Legacy repository-level runtime/config duplicates must not exist; the extension is the single runtime source of truth."))

    if not os.path.isfile(manifest_path):
        findings.append(finding("EXTENSION_MANIFEST_MISSING", "extension.json is missing."))
    else:
        manifest = _read_json(manifest_path, "EXTENSION_MANIFEST_INVALID", findings)
        if isinstance(manifest, dict):
            if manifest.get("name") != "Revit Estimating Tools":
                findings.append(finding("EXTENSION_NAME_INVALID", "extension.json has an unexpected name."))
        elif manifest is not None:
            findings.append(finding("EXTENSION_MANIFEST_INVALID", "extension.json root must be an object."))

    if os.path.exists(os.path.join(extension, "extension.yaml")):
        findings.append(finding("LEGACY_EXTENSION_MANIFEST", "Legacy extension.yaml should not be present."))

    for relative in EXPECTED_BUTTONS:
        button_dir = os.path.join(extension, relative)
        script_path = os.path.join(button_dir, "script.py")
        bundle_path = os.path.join(button_dir, "bundle.yaml")
        if not os.path.isfile(script_path):
            findings.append(finding("BUTTON_SCRIPT_MISSING", "Expected pyRevit button script is missing.", {"button": relative}))
            continue
        if not os.path.isfile(bundle_path):
            findings.append(finding("BUTTON_BUNDLE_MISSING", "Expected bundle.yaml is missing.", {"button": relative}))
            continue

        script_text = _read_text(script_path)
        if "sys.path.insert" in script_text or 'os.path.join(ROOT, "lib")' in script_text:
            findings.append(finding("BUTTON_PATH_HACK_DETECTED", "Button script must rely on the pyRevit extension lib path instead of repository-relative sys.path injection.", {"button": relative}))
        first_line = script_text.splitlines()[0].lower() if script_text.splitlines() else ""
        if "python3" in first_line:
            findings.append(finding("UNSUPPORTED_BUTTON_ENGINE", "V0.1 button must remain on default IronPython while using current pyRevit forms helpers.", {"button": relative}))
        for token in ("DB.Transaction(", "TransactionGroup(", "SubTransaction("):
            if token in script_text:
                findings.append(finding("WRITE_TRANSACTION_DETECTED", "Read-only V0.1 button contains a Revit transaction token.", {"button": relative, "token": token}))

        bundle_text = _read_text(bundle_path).lower()
        if "min_revit_version: 2021" not in bundle_text:
            findings.append(finding("MIN_REVIT_VERSION_MISSING", "bundle.yaml must declare minimum Revit 2021.", {"button": relative}))
        if "engine:" not in bundle_text or "clean: true" not in bundle_text:
            findings.append(finding("CLEAN_ENGINE_MISSING", "bundle.yaml must declare clean engine behavior.", {"button": relative}))
        has_project_context = "context: doc-project" in bundle_text
        if relative in MODEL_BUTTONS and not has_project_context:
            findings.append(finding("PROJECT_CONTEXT_MISSING", "Model command must require a project document.", {"button": relative}))
        if relative not in MODEL_BUTTONS and has_project_context:
            findings.append(finding("FILE_COMMAND_CONTEXT_TOO_STRICT", "File-based command should not require an active project document.", {"button": relative}))

    if not os.path.isfile(categories_path):
        findings.append(finding("CATEGORY_CONFIG_MISSING", "config/categories.json is missing."))
    else:
        data = _read_json(categories_path, "CATEGORY_CONFIG_INVALID", findings)
        if isinstance(data, dict) and data.get("schema_version") != SCHEMA_VERSION:
            findings.append(finding("CATEGORY_SCHEMA_VERSION_UNSUPPORTED", "categories.json schema_version does not match the tool schema.", {"actual": data.get("schema_version"), "expected": SCHEMA_VERSION}))
        categories = data.get("categories") if isinstance(data, dict) else None
        if not isinstance(categories, list) or not categories:
            findings.append(finding("CATEGORY_CONFIG_INVALID", "categories.json must contain a non-empty categories list."))
        else:
            seen_names = set()
            seen_bics = set()
            for index, item in enumerate(categories):
                if not isinstance(item, dict):
                    findings.append(finding("CATEGORY_SPEC_INVALID", "Category spec must be an object.", {"index": index}))
                    continue
                name = item.get("name")
                bic = item.get("bic")
                quantity = item.get("primary_quantity")
                if not name or not bic:
                    findings.append(finding("CATEGORY_SPEC_INCOMPLETE", "Category spec must define name and bic.", {"index": index}))
                if name in seen_names:
                    findings.append(finding("CATEGORY_NAME_DUPLICATE", "Duplicate category name.", {"name": name}))
                if bic in seen_bics:
                    findings.append(finding("CATEGORY_BIC_DUPLICATE", "Duplicate BuiltInCategory mapping.", {"bic": bic}))
                seen_names.add(name)
                seen_bics.add(bic)
                if quantity not in ALLOWED_PRIMARY_QUANTITIES:
                    findings.append(finding("PRIMARY_QUANTITY_INVALID", "Unsupported primary quantity type.", {"name": name, "primary_quantity": quantity}))
                for flag in ("audit_only", "requires_size", "requires_system"):
                    if flag in item and not isinstance(item.get(flag), bool):
                        findings.append(finding("CATEGORY_FLAG_INVALID", "Category boolean flag has a non-boolean value.", {"name": name, "flag": flag, "value": item.get(flag)}))

    for path in schemas:
        if not os.path.isfile(path):
            findings.append(finding("SCHEMA_FILE_MISSING", "Required schema file is missing.", {"path": os.path.relpath(path, repository_root or root)}))
        else:
            data = _read_json(path, "SCHEMA_JSON_INVALID", findings)
            if data is not None and not isinstance(data, dict):
                findings.append(finding("SCHEMA_JSON_INVALID", "Schema root must be an object.", {"path": os.path.relpath(path, root)}))

    return findings


def doctor_passed(findings):
    return validation_passed(findings)
