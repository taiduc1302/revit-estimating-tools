# -*- coding: utf-8 -*-
"""Revit document/link and category collectors."""
from __future__ import absolute_import, print_function

from pyrevit import DB

from .hashing import sha256_text
from .parameters import element_id_value
from .utils import to_text


def _document_path(doc):
    try:
        path = doc.PathName
        if path:
            return to_text(path)
    except Exception:
        pass
    return to_text(getattr(doc, "Title", "Unsaved Model"))


def document_identity(doc):
    return _document_path(doc)


def _link_name(link_instance):
    try:
        return to_text(link_instance.Name)
    except Exception:
        return "Revit Link"


def collect_document_contexts(host_doc):
    contexts = [{
        "doc": host_doc,
        "document_id": sha256_text(document_identity(host_doc))[:16],
        "document_identity": document_identity(host_doc),
        "source_document": to_text(host_doc.Title),
        "is_linked": False,
        "link_instance_name": None,
        "link_instance_id": None,
        "link_instance_unique_id": None,
        "transform": None,
    }]
    link_issues = []
    instances = DB.FilteredElementCollector(host_doc).OfClass(DB.RevitLinkInstance).ToElements()
    for instance in instances:
        link_doc = None
        try:
            link_doc = instance.GetLinkDocument()
        except Exception:
            link_doc = None
        if link_doc is None:
            link_issues.append({
                "rule_id": "LINK_UNLOADED", "severity": "HIGH", "source_document": to_text(host_doc.Title),
                "message": "Revit link is unloaded or unavailable: %s" % _link_name(instance),
                "values": {"link_instance_id": element_id_value(instance.Id), "link_instance_name": _link_name(instance)}
            })
            continue
        try:
            transform = instance.GetTotalTransform()
        except Exception:
            try:
                transform = instance.GetTransform()
            except Exception:
                transform = None
        contexts.append({
            "doc": link_doc,
            "document_id": sha256_text(document_identity(link_doc))[:16],
            "document_identity": document_identity(link_doc),
            "source_document": to_text(link_doc.Title),
            "is_linked": True,
            "link_instance_name": _link_name(instance),
            "link_instance_id": element_id_value(instance.Id),
            "link_instance_unique_id": to_text(getattr(instance, "UniqueId", "")),
            "transform": transform,
        })
    return contexts, link_issues


def collect_category_elements(context, spec):
    bic = getattr(DB.BuiltInCategory, spec.get("bic", ""), None)
    if bic is None:
        return []
    try:
        return list(
            DB.FilteredElementCollector(context["doc"])
            .OfCategory(bic)
            .WhereElementIsNotElementType()
            .ToElements()
        )
    except Exception:
        return []
