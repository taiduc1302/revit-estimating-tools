# -*- coding: utf-8 -*-
"""Small dependency-free compatibility helpers."""
from __future__ import absolute_import, division, print_function

import math

try:
    text_type = unicode  # type: ignore[name-defined]
    binary_type = str
except NameError:  # pragma: no cover - Python 3
    text_type = str
    binary_type = bytes


def to_text(value):
    if value is None:
        return u""
    if isinstance(value, text_type):
        return value
    if isinstance(value, binary_type):
        try:
            return value.decode("utf-8", "replace")
        except AttributeError:
            return text_type(value)
    try:
        return text_type(value)
    except Exception:
        return text_type(repr(value))


def is_number(value):
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return not (math.isnan(number) or math.isinf(number))


def rounded(value, digits=6):
    if value is None or not is_number(value):
        return None
    return round(float(value), digits)


def first_non_empty(values):
    for value in values:
        if value is None:
            continue
        if to_text(value).strip():
            return value
    return None


def nested_get(data, dotted_key, default=None):
    value = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value
