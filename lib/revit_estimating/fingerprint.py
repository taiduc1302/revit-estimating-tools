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
    size = element.get("size") or {}
    parts = []
    for key in ("diameter_mm", "width_mm", "height_mm", "size_text"):
        value = size.get(key)
        if value not in (None, ""):
            parts.append("%s=%s" % (key, to_text(value)))
    return ";".join(parts)


def strict_fingerprint(element):
    values = [
        element.get("category"), element.get("family"), element.get("type"),
        element.get("system"), element.get("material"), element.get("level"),
        element.get("mark"), size_label(element),
        _rounded_location(element.get("location"), 0.10),
    ]
    return sha256_text("|".join([_norm(x) for x in values]))


def loose_fingerprint(element):
    values = [
        element.get("category"), element.get("family"), element.get("level"),
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


def similarity_score(left, right):
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
