# -*- coding: utf-8 -*-
"""Safe Revit parameter access. Imported only inside Revit/pyRevit."""
from __future__ import absolute_import, print_function

from pyrevit import DB

from .utils import to_text


def element_id_value(element_id):
    if element_id is None:
        return None
    try:
        return int(element_id.Value)
    except Exception:
        try:
            return int(element_id.IntegerValue)
        except Exception:
            return None


def built_in_parameter(name):
    return getattr(DB.BuiltInParameter, name, None)


def get_parameter(element, built_in_names=None, lookup_names=None):
    if element is None:
        return None
    for name in built_in_names or []:
        bip = built_in_parameter(name)
        if bip is None:
            continue
        try:
            param = element.get_Parameter(bip)
            if param is not None and param.HasValue:
                return param
        except Exception:
            pass
    for name in lookup_names or []:
        try:
            param = element.LookupParameter(name)
            if param is not None and param.HasValue:
                return param
        except Exception:
            pass
    return None


def parameter_double(param):
    if param is None:
        return None
    try:
        if param.StorageType == DB.StorageType.Double:
            return float(param.AsDouble())
    except Exception:
        pass
    return None


def _element_name(doc, element_id):
    try:
        element = doc.GetElement(element_id)
        if element is None:
            return None
        try:
            return to_text(element.Name)
        except Exception:
            return to_text(DB.Element.Name.GetValue(element))
    except Exception:
        return None


def parameter_text(param, doc=None):
    if param is None:
        return None
    try:
        storage = param.StorageType
        if storage == DB.StorageType.String:
            return param.AsString()
        if storage == DB.StorageType.Integer:
            return to_text(param.AsInteger())
        if storage == DB.StorageType.ElementId:
            element_id = param.AsElementId()
            resolved = _element_name(doc, element_id) if doc is not None else None
            return resolved or to_text(element_id_value(element_id))
        if storage == DB.StorageType.Double:
            try:
                display = param.AsValueString()
                if display:
                    return display
            except Exception:
                pass
            return to_text(param.AsDouble())
    except Exception:
        pass
    return None


def first_double(elements, built_in_names=None, lookup_names=None):
    for element in elements:
        value = parameter_double(get_parameter(element, built_in_names, lookup_names))
        if value is not None:
            return value
    return None


def first_text(elements, doc, built_in_names=None, lookup_names=None):
    for element in elements:
        value = parameter_text(get_parameter(element, built_in_names, lookup_names), doc)
        if value not in (None, ""):
            return value
    return None
