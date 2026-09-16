# -*- coding: utf-8 -*-
"""Estimating-focused model audit rules."""
from __future__ import absolute_import, print_function

from .config import spec_by_name
from .hashing import sha256_text
from .utils import to_text, is_number

MATERIAL_EXPECTED = set(["Pipes", "Conduits", "Cable Trays", "Ducts", "Structural Foundations", "Structural Framing", "Floors", "Walls"])


def _issue(rule_id, severity, message, element=None, source_document=None, values=None):
    element = element or {}
    element_key = element.get("element_key")
    identity = "%s|%s|%s" % (rule_id, element_key or "MODEL", message)
    return {
        "issue_id": sha256_text(identity)[:16],
        "rule_id": rule_id,
        "severity": severity,
        "element_key": element_key,
        "element_id": element.get("element_id"),
        "unique_id": element.get("unique_id"),
        "source_document": source_document or element.get("source_document"),
        "category": element.get("category"),
        "message": message,
        "values": values or {},
    }


def _has_size(element):
    size = element.get("size") or {}
    return any(size.get(key) not in (None, "") for key in ("diameter_mm", "width_mm", "height_mm", "size_text"))


def audit_element(element):
    issues = []
    category = element.get("category")
    spec = spec_by_name(category) or {}

    if category == "Generic Models":
        issues.append(_issue("GENERIC_MODEL", "MEDIUM", "Generic Model may require manual estimating review.", element))

    if category in MATERIAL_EXPECTED and not to_text(element.get("material")).strip():
        issues.append(_issue("MISSING_MATERIAL", "MEDIUM", "Material is missing or could not be resolved.", element))

    if spec.get("requires_size") and not _has_size(element):
        issues.append(_issue("MISSING_SIZE", "HIGH", "Required estimating size is missing.", element))

    if spec.get("requires_system") and not to_text(element.get("system")).strip():
        issues.append(_issue("MISSING_SYSTEM", "MEDIUM", "System classification/name is missing.", element))

    if category != "Generic Models" and not to_text(element.get("level")).strip():
        issues.append(_issue("MISSING_LEVEL", "LOW", "Level or reference level is missing.", element))

    primary_value = element.get("primary_quantity_value")
    if element.get("primary_quantity_type") and (not is_number(primary_value) or float(primary_value) <= 0):
        issues.append(_issue(
            "INVALID_PRIMARY_QUANTITY", "HIGH", "Primary estimating quantity is missing, zero, or invalid.", element,
            values={"quantity_type": element.get("primary_quantity_type"), "value": primary_value}
        ))

    if not to_text(element.get("type")).strip():
        issues.append(_issue("MISSING_TYPE", "MEDIUM", "Element type could not be resolved.", element))

    if to_text(element.get("design_option")).strip():
        issues.append(_issue("DESIGN_OPTION", "INFO", "Element belongs to a design option.", element, values={"design_option": element.get("design_option")}))

    if to_text(element.get("phase_demolished")).strip():
        issues.append(_issue("DEMOLISHED_ELEMENT", "INFO", "Element has a demolition phase.", element, values={"phase_demolished": element.get("phase_demolished")}))

    phase_created = to_text(element.get("phase_created")).lower()
    if "existing" in phase_created or phase_created.startswith("exist"):
        issues.append(_issue("EXISTING_PHASE", "INFO", "Element appears to be in an existing phase.", element, values={"phase_created": element.get("phase_created")}))

    return issues


def audit_model(elements, link_issues=None):
    issues = []
    for element in elements:
        issues.extend(audit_element(element))
    for item in link_issues or []:
        issues.append(_issue(
            item.get("rule_id", "LINK_ISSUE"), item.get("severity", "HIGH"),
            item.get("message", "Linked model issue."), source_document=item.get("source_document"),
            values=item.get("values") or {}
        ))
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    return sorted(issues, key=lambda x: (severity_order.get(x.get("severity"), 9), to_text(x.get("source_document")), to_text(x.get("element_key")), x.get("rule_id", "")))


def audit_summary(issues):
    result = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for issue in issues:
        severity = issue.get("severity", "INFO")
        result[severity] = result.get(severity, 0) + 1
    result["TOTAL"] = len(issues)
    return result
