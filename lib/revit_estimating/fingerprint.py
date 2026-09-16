# -*- coding: utf-8 -*-
"""Element fingerprinting and conservative recreated-element matching."""
from __future__ import absolute_import, division, print_function

from .hashing import sha256_text
from .utils import to_text, is_number


def _norm(value):
    return to_text(value).strip().lower()


def _rounded_location(location, increment):
    if not isinstance(location, dict):
        return ""
    values = []
    for key in ("x_m", "y_m", "z_m"):
        value = location.get(key)
        if not is_number(value):
            values.append("")
        else:
            values.append(str(round(float(value) / increment) * increment))
    return "|".join(values)


def size_label(element):
    """Return a canonical physical-size label, avoiding display-unit formatting noise."""
    size = element.get("size") or {}
    parts = []
    for key in ("diameter_mm", "width_mm", "height_mm"):
        value = size.get(key)
        if is_number(value):
            parts.append("%s=%s" % (key, to_text(round(float(value), 3))))
    if parts:
        return ";".join(parts)
    size_text = to_text(size.get("size_text")).strip()
    return "size_text=%s" % size_text if size_text else ""


def strict_fingerprint(element):
    values = [
        element.get("source_scope_key"), element.get("category"), element.get("family"), element.get("type"),
        element.get("system"), element.get("material"), element.get("level"),
        element.get("mark"), size_label(element),
        _rounded_location(element.get("location"), 0.10),
    ]
    return sha256_text("|".join([_norm(x) for x in values]))


def loose_fingerprint(element):
    values = [
        element.get("source_scope_key"), element.get("category"), element.get("family"), element.get("level"),
        element.get("mark"), _rounded_location(element.get("location"), 0.50),
    ]
    return sha256_text("|".join([_norm(x) for x in values]))


def _location_score(left, right):
    a = left.get("location") or {}
    b = right.get("location") or {}
    coords = []
    for key in ("x_m", "y_m", "z_m"):
        if not is_number(a.get(key)) or not is_number(b.get(key)):
            return 0.0
        coords.append(float(a[key]) - float(b[key]))
    distance = sum([x * x for x in coords]) ** 0.5
    if distance <= 0.10:
        return 1.0
    if distance <= 0.50:
        return 0.75
    if distance <= 2.0:
        return 0.35
    return 0.0


def _same_scope(left, right):
    """Prevent inferred recreated-element matches from crossing model/link scopes."""
    if bool(left.get("is_linked")) != bool(right.get("is_linked")):
        return False
    left_scope = to_text(left.get("source_scope_key")).strip()
    right_scope = to_text(right.get("source_scope_key")).strip()
    if left_scope and right_scope:
        return left_scope == right_scope
    if bool(left.get("is_linked")):
        left_link = to_text(left.get("link_instance_unique_id")).strip()
        right_link = to_text(right.get("link_instance_unique_id")).strip()
        if left_link and right_link:
            return left_link == right_link
    return True


def similarity_score(left, right):
    if not _same_scope(left, right):
        return 0.0
    if _norm(left.get("category")) != _norm(right.get("category")):
        return 0.0
    score = 0.25
    weighted = [
        ("family", 0.12), ("type", 0.10), ("system", 0.10),
        ("material", 0.08), ("level", 0.10), ("mark", 0.10),
    ]
    for key, weight in weighted:
        a = _norm(left.get(key))
        b = _norm(right.get(key))
        if a and b and a == b:
            score += weight
    if size_label(left) and size_label(left) == size_label(right):
        score += 0.05
    score += 0.10 * _location_score(left, right)
    return round(score, 4)
