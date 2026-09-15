# -*- coding: utf-8 -*-
"""Category configuration with a built-in fallback for robust deployment."""
from __future__ import absolute_import, print_function

import json
import os

DEFAULT_CATEGORY_SPECS = [
    {"name": "Pipes", "bic": "OST_PipeCurves", "primary_quantity": "LENGTH", "requires_size": True, "requires_system": True},
    {"name": "Pipe Fittings", "bic": "OST_PipeFitting", "primary_quantity": "COUNT"},
    {"name": "Pipe Accessories", "bic": "OST_PipeAccessory", "primary_quantity": "COUNT"},
    {"name": "Conduits", "bic": "OST_Conduit", "primary_quantity": "LENGTH", "requires_size": True},
    {"name": "Conduit Fittings", "bic": "OST_ConduitFitting", "primary_quantity": "COUNT"},
    {"name": "Cable Trays", "bic": "OST_CableTray", "primary_quantity": "LENGTH", "requires_size": True},
    {"name": "Cable Tray Fittings", "bic": "OST_CableTrayFitting", "primary_quantity": "COUNT"},
    {"name": "Ducts", "bic": "OST_DuctCurves", "primary_quantity": "LENGTH", "requires_size": True, "requires_system": True},
    {"name": "Duct Fittings", "bic": "OST_DuctFitting", "primary_quantity": "COUNT"},
    {"name": "Mechanical Equipment", "bic": "OST_MechanicalEquipment", "primary_quantity": "COUNT"},
    {"name": "Structural Foundations", "bic": "OST_StructuralFoundation", "primary_quantity": "VOLUME"},
    {"name": "Structural Framing", "bic": "OST_StructuralFraming", "primary_quantity": "LENGTH"},
    {"name": "Floors", "bic": "OST_Floors", "primary_quantity": "AREA"},
    {"name": "Walls", "bic": "OST_Walls", "primary_quantity": "AREA"},
    {"name": "Generic Models", "bic": "OST_GenericModel", "primary_quantity": "COUNT", "audit_only": True}
]


def repository_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_category_specs():
    path = os.path.join(repository_root(), "config", "categories.json")
    try:
        with open(path, "r") as stream:
            data = json.load(stream)
        specs = data.get("categories", data)
        if isinstance(specs, list) and specs:
            return specs
    except Exception:
        pass
    return list(DEFAULT_CATEGORY_SPECS)


def spec_by_name(name):
    for spec in load_category_specs():
        if spec.get("name") == name:
            return spec
    return None
