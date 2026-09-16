# -*- coding: utf-8 -*-
"""Deterministic JSON and CSV serialization without third-party packages."""
from __future__ import absolute_import, print_function

import io
import json
import os
import re

from .utils import to_text


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
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    return to_text(text) + u"\n"


def write_text(path, content):
    with io.open(path, "w", encoding="utf-8") as stream:
        stream.write(to_text(content))


def write_json(path, data, pretty=True):
    write_text(path, canonical_json(data, pretty=pretty))


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as stream:
        return json.loads(stream.read())


def _csv_cell(value):
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    text = to_text(value)
    if any(ch in text for ch in [u",", u"\"", u"\n", u"\r"]):
        return u'"' + text.replace(u'"', u'""') + u'"'
    return text


def write_csv(path, rows, columns):
    lines = [u",".join([_csv_cell(column) for column in columns])]
    for row in rows:
        lines.append(u",".join([_csv_cell(row.get(column)) for column in columns]))
    write_text(path, u"\n".join(lines) + u"\n")
