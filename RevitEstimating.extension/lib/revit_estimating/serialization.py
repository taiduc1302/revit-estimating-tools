# -*- coding: utf-8 -*-
"""Deterministic JSON and CSV serialization without third-party packages."""
from __future__ import absolute_import, print_function

import io
import json
import os
import re

from .utils import to_text, text_type, binary_type


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def sanitize_filename(value, default="Model"):
    value = to_text(value).strip() or default
    value = re.sub(r"[<>:\\/?*\"|]+", "_", value)
    value = re.sub(r"\s+", "_", value).strip("._")
    return value or default


def canonical_json(data, pretty=True):
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    return to_text(text) + u"\n"


def write_text(path, content):
    with io.open(path, "w", encoding="utf-8") as stream:
        stream.write(to_text(content))


def write_json(path, data, pretty=True):
    write_text(path, canonical_json(data, pretty=pretty))


def read_text(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return stream.read()


def _reject_non_finite_json(value):
    raise ValueError("Non-finite JSON number is not allowed: %s" % value)


def read_json(path):
    return json.loads(read_text(path), parse_constant=_reject_non_finite_json)


def _spreadsheet_safe_text(text):
    """Prevent formula-like text values from being executed by spreadsheet applications."""
    candidate = text.lstrip(u" \t\r")
    if candidate[:1] in (u"=", u"+", u"-", u"@"):
        return u"'" + text
    return text


def _csv_cell(value):
    is_text_value = isinstance(value, (text_type, binary_type))
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
        is_text_value = False
    text = to_text(value)
    if is_text_value:
        text = _spreadsheet_safe_text(text)
    if any(ch in text for ch in [u",", u"\"", u"\n", u"\r"]):
        return u'"' + text.replace(u'"', u'""') + u'"'
    return text


def csv_text(rows, columns):
    lines = [u",".join([_csv_cell(column) for column in columns])]
    for row in rows:
        lines.append(u",".join([_csv_cell(row.get(column)) for column in columns]))
    return u"\n".join(lines) + u"\n"


def write_csv(path, rows, columns):
    write_text(path, csv_text(rows, columns))
