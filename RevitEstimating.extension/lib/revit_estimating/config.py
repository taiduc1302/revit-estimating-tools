# -*- coding: utf-8 -*-
"""Required, fail-closed category configuration with command-local caching."""
from __future__ import absolute_import, print_function

import io
import json
import os

from . import SCHEMA_VERSION
from .hashing import sha256_file

ALLOWED_PRIMARY_QUANTITIES = set(("LENGTH", "AREA", "VOLUME", "COUNT"))
_BOOLEAN_FLAGS = ("audit_only", "requires_size", "requires_system")
_CATEGORY_CACHE = None
_CATEGORY_EVIDENCE = None


def repository_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def category_config_path():
    return os.path.join(repository_root(), "config", "categories.json")


def _read_category_config(path):
    if not os.path.isfile(path):
        raise ValueError("Required category configuration is missing: %s" % path)
    try:
        with io.open(path, "r", encoding="utf-8-sig") as stream:
            data = json.loads(stream.read())
    except Exception as exc:
        raise ValueError("Category configuration could not be parsed: %s (%s)" % (path, exc))
    if not isinstance(data, dict):
        raise ValueError("Category configuration root must be an object: %s" % path)
    return data


def _validated_specs(data, path):
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            "Category configuration schema_version %s is not supported; expected %s: %s"
            % (version, SCHEMA_VERSION, path)
        )
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("Category configuration must contain a non-empty categories list: %s" % path)

    seen_names = set()
    seen_bics = set()
    specs = []
    for index, item in enumerate(categories):
        if not isinstance(item, dict):
            raise ValueError("Category spec at index %s must be an object: %s" % (index, path))
        name = item.get("name")
        bic = item.get("bic")
        quantity = item.get("primary_quantity")
        if not name or not bic:
            raise ValueError("Category spec at index %s must define name and bic: %s" % (index, path))
        if name in seen_names:
            raise ValueError("Duplicate category name %s in %s" % (name, path))
        if bic in seen_bics:
            raise ValueError("Duplicate BuiltInCategory mapping %s in %s" % (bic, path))
        if quantity not in ALLOWED_PRIMARY_QUANTITIES:
            raise ValueError("Unsupported primary quantity %s for %s in %s" % (quantity, name, path))
        for flag in _BOOLEAN_FLAGS:
            if flag in item and not isinstance(item.get(flag), bool):
                raise ValueError("Category flag %s must be boolean for %s in %s" % (flag, name, path))
        seen_names.add(name)
        seen_bics.add(bic)
        specs.append(dict(item))
    return tuple(specs)


def load_category_specs(force_reload=False):
    global _CATEGORY_CACHE, _CATEGORY_EVIDENCE
    if force_reload:
        _CATEGORY_CACHE = None
        _CATEGORY_EVIDENCE = None
    if _CATEGORY_CACHE is not None:
        return _CATEGORY_CACHE

    path = category_config_path()
    data = _read_category_config(path)
    specs = _validated_specs(data, path)
    evidence = {
        "path": os.path.join("config", "categories.json").replace(os.sep, "/"),
        "sha256": sha256_file(path),
        "schema_version": data.get("schema_version"),
        "category_count": len(specs),
        "mode": "REQUIRED_FAIL_CLOSED",
    }
    _CATEGORY_CACHE = specs
    _CATEGORY_EVIDENCE = evidence
    return _CATEGORY_CACHE


def category_config_evidence(force_reload=False):
    load_category_specs(force_reload=force_reload)
    return dict(_CATEGORY_EVIDENCE)


def spec_by_name(name):
    for spec in load_category_specs():
        if spec.get("name") == name:
            return spec
    return None
