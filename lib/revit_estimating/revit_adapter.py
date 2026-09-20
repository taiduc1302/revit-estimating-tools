# -*- coding: utf-8 -*-
"""Read-only adapter from the Revit API to normalized estimating DTOs."""
from __future__ import absolute_import, division, print_function

from pyrevit import DB

from .collectors import collect_document_contexts, collect_category_elements
from .config import load_category_specs, category_config_evidence
from .fingerprint import strict_fingerprint, loose_fingerprint
from .normalization import length_ft_to_m, length_ft_to_mm, area_sqft_to_sqm, volume_cuft_to_cum
from .parameters import element_id_value, first_double, first_text, get_parameter, parameter_text
from .utils import to_text


def _type_element(element, doc):
    try:
        type_id = element.GetTypeId()
        if type_id is not None and element_id_value(type_id) not in (None, -1):
            return doc.GetElement(type_id)
    except Exception:
        pass
    return None


def _element_name(element):
    if element is None:
        return None
    try:
        return to_text(element.Name)
    except Exception:
        try:
            return to_text(DB.Element.Name.GetValue(element))
        except Exception:
            return None


def _family_name(element, type_element):
    try:
        symbol = element.Symbol
        family = symbol.Family
        name = _element_name(family)
        if name:
            return name
    except Exception:
        pass
    try:
        value = type_element.FamilyName
        if value:
            return to_text(value)
    except Exception:
        pass
    return None


def _level_name(element, doc):
    built_ins = [
        "RBS_START_LEVEL_PARAM",
        "LEVEL_PARAM",
        "FAMILY_LEVEL_PARAM",
        "INSTANCE_REFERENCE_LEVEL_PARAM",
        "INSTANCE_SCHEDULE_ONLY_LEVEL_PARAM",
        "SCHEDULE_LEVEL_PARAM",
        "SCHEDULE_BASE_LEVEL_PARAM",
    ]
    param = get_parameter(element, built_ins, ["Level", "Reference Level", "Base Level"])
    value = parameter_text(param, doc)
    if value:
        return value
    try:
        level_id = element.LevelId
        level = doc.GetElement(level_id)
        return _element_name(level)
    except Exception:
        return None


def _workset_name(element, doc):
    try:
        if not doc.IsWorkshared:
            return None
        workset = doc.GetWorksetTable().GetWorkset(element.WorksetId)
        return _element_name(workset)
    except Exception:
        return None


def _design_option_name(element):
    try:
        option = element.DesignOption
        return _element_name(option)
    except Exception:
        return None


def _phase_name(element, doc, bip_name):
    return first_text([element], doc, [bip_name], [])


def _location(element, transform=None):
    point = None
    try:
        location = element.Location
        if isinstance(location, DB.LocationPoint):
            point = location.Point
        elif isinstance(location, DB.LocationCurve):
            point = location.Curve.Evaluate(0.5, True)
    except Exception:
        point = None
    if point is None:
        try:
            box = element.get_BoundingBox(None)
            if box:
                point = (box.Min + box.Max) * 0.5
        except Exception:
            point = None
    if point is None:
        return None
    if transform is not None:
        try:
            point = transform.OfPoint(point)
        except Exception:
            pass
    return {"x_m": round(point.X * 0.3048, 3), "y_m": round(point.Y * 0.3048, 3), "z_m": round(point.Z * 0.3048, 3)}


def _size(element, type_element, doc):
    items = [element, type_element]
    diameter = first_double(items, ["RBS_PIPE_DIAMETER_PARAM", "RBS_CONDUIT_DIAMETER_PARAM", "RBS_CURVE_DIAMETER_PARAM"], ["Diameter"])
    width = first_double(items, ["RBS_CURVE_WIDTH_PARAM", "RBS_CABLETRAY_WIDTH_PARAM"], ["Width"])
    height = first_double(items, ["RBS_CURVE_HEIGHT_PARAM", "RBS_CABLETRAY_HEIGHT_PARAM"], ["Height"])
    size_text = first_text(items, doc, ["RBS_CALCULATED_SIZE", "RBS_DUCT_SIZE_FORMATTED_PARAM"], ["Size"])
    return {
        "diameter_mm": length_ft_to_mm(diameter),
        "width_mm": length_ft_to_mm(width),
        "height_mm": length_ft_to_mm(height),
        "size_text": size_text,
    }


def _quantities(element, spec):
    raw_length = first_double(
        [element],
        ["CURVE_ELEM_LENGTH", "INSTANCE_LENGTH_PARAM", "RBS_CABLETRAYCONDUITRUN_LENGTH_PARAM"],
        ["Length"],
    )
    if raw_length is None:
        try:
            location = element.Location
            if isinstance(location, DB.LocationCurve):
                raw_length = float(location.Curve.Length)
        except Exception:
            pass
    raw_area = first_double([element], ["HOST_AREA_COMPUTED"], ["Area"])
    raw_volume = first_double([element], ["HOST_VOLUME_COMPUTED", "RBS_PIPE_VOLUME_PARAM"], ["Volume"])
    quantities = {
        "raw_internal_length_ft": raw_length,
        "raw_internal_area_sqft": raw_area,
        "raw_internal_volume_cuft": raw_volume,
        "length_m": length_ft_to_m(raw_length),
        "area_m2": area_sqft_to_sqm(raw_area),
        "volume_m3": volume_cuft_to_cum(raw_volume),
        "count_ea": 1,
    }
    primary_type = spec.get("primary_quantity")
    if primary_type == "LENGTH":
        return quantities, primary_type, quantities["length_m"], "M"
    if primary_type == "AREA":
        return quantities, primary_type, quantities["area_m2"], "M2"
    if primary_type == "VOLUME":
        return quantities, primary_type, quantities["volume_m3"], "M3"
    return quantities, "COUNT", 1, "EA"


def _selected_parameters(element, type_element, doc):
    items = [element, type_element]
    return {
        "description": first_text(items, doc, ["ALL_MODEL_DESCRIPTION"], ["Description"]),
        "comments": first_text([element], doc, ["ALL_MODEL_INSTANCE_COMMENTS"], ["Comments"]),
        "type_comments": first_text([type_element], doc, ["ALL_MODEL_TYPE_COMMENTS"], ["Type Comments"]),
        "assembly_code": first_text(items, doc, ["UNIFORMAT_CODE"], ["Assembly Code"]),
        "keynote": first_text(items, doc, ["KEYNOTE_PARAM"], ["Keynote"]),
        "model": first_text(items, doc, ["ALL_MODEL_MODEL"], ["Model"]),
    }


def _source_scope_key(context):
    """Stable logical model/link scope for comparing snapshots across Save As/renames."""
    if context.get("is_linked"):
        return "LINK:%s" % (to_text(context.get("link_instance_unique_id")).strip() or to_text(context.get("link_instance_name")).strip())
    return "HOST"


def extract_element(element, context, spec):
    doc = context["doc"]
    type_element = _type_element(element, doc)
    items = [element, type_element]
    system = first_text(
        items,
        doc,
        [
            "RBS_SYSTEM_NAME_PARAM",
            "RBS_PIPING_SYSTEM_TYPE_PARAM",
            "RBS_DUCT_SYSTEM_TYPE_PARAM",
            "RBS_CABLETRAYCONDUIT_SYSTEM_TYPE",
            "RBS_SYSTEM_CLASSIFICATION_PARAM",
            "RBS_CTC_SERVICE_TYPE",
        ],
        ["System Name", "System Type", "System Classification", "Service Type"],
    )
    material = first_text(
        items,
        doc,
        ["RBS_PIPE_MATERIAL_PARAM", "STRUCTURAL_MATERIAL_PARAM", "MATERIAL_ID_PARAM"],
        ["Material"],
    )
    mark = first_text([element], doc, ["ALL_MODEL_MARK"], ["Mark"])
    quantities, primary_type, primary_value, primary_unit = _quantities(element, spec)
    unique_id = to_text(getattr(element, "UniqueId", ""))
    link_uid = context.get("link_instance_unique_id")
    scope_key = _source_scope_key(context)
    key_parts = [scope_key, unique_id or to_text(element_id_value(element.Id))]
    dto = {
        "element_key": ":".join([to_text(x) for x in key_parts if x]),
        "source_scope_key": scope_key,
        "source_document": context.get("source_document"),
        "source_document_id": context.get("document_id"),
        "source_document_identity": context.get("document_identity"),
        "is_linked": bool(context.get("is_linked")),
        "link_instance_name": context.get("link_instance_name"),
        "link_instance_id": context.get("link_instance_id"),
        "link_instance_unique_id": link_uid,
        "element_id": element_id_value(element.Id),
        "unique_id": unique_id,
        "category": spec.get("name"),
        "family": _family_name(element, type_element),
        "type": _element_name(type_element),
        "system": system,
        "material": material,
        "level": _level_name(element, doc),
        "workset": _workset_name(element, doc),
        "phase_created": _phase_name(element, doc, "PHASE_CREATED"),
        "phase_demolished": _phase_name(element, doc, "PHASE_DEMOLISHED"),
        "design_option": _design_option_name(element),
        "mark": mark,
        "size": _size(element, type_element, doc),
        "location": _location(element, context.get("transform")),
        "quantities": quantities,
        "primary_quantity_type": primary_type,
        "primary_quantity_value": primary_value,
        "primary_quantity_unit": primary_unit,
        "quantity_aggregation_excluded": bool(spec.get("audit_only")),
        "parameters": _selected_parameters(element, type_element, doc),
    }
    dto["fingerprints"] = {
        "strict": strict_fingerprint(dto),
        "loose": loose_fingerprint(dto),
    }
    return dto


def model_metadata(host_doc, contexts, app=None):
    try:
        project_info = host_doc.ProjectInformation
        project_name = first_text([project_info], host_doc, ["PROJECT_NAME"], ["Project Name"]) or to_text(host_doc.Title)
        project_number = first_text([project_info], host_doc, ["PROJECT_NUMBER"], ["Project Number"])
    except Exception:
        project_name = to_text(host_doc.Title)
        project_number = None
    application = app or getattr(host_doc, "Application", None)
    linked = []
    for context in contexts:
        if context.get("is_linked"):
            linked.append({
                "source_scope_key": _source_scope_key(context),
                "document": context.get("source_document"),
                "document_identity": context.get("document_identity"),
                "link_instance_name": context.get("link_instance_name"),
                "link_instance_id": context.get("link_instance_id"),
                "link_instance_unique_id": context.get("link_instance_unique_id"),
            })
    return {
        "project_name": project_name,
        "project_number": project_number,
        "host_source_scope_key": "HOST",
        "host_document": to_text(host_doc.Title),
        "host_document_identity": contexts[0].get("document_identity") if contexts else None,
        "revit_version": to_text(getattr(application, "VersionNumber", "")),
        "is_workshared": bool(getattr(host_doc, "IsWorkshared", False)),
        "linked_models": linked,
        "source_model_hash": None,
        "source_model_hash_status": "NOT_COMPUTED_FOR_OPEN_MODEL",
    }


def extract_model(host_doc, app=None):
    category_specs = load_category_specs()
    config_evidence = category_config_evidence()
    contexts, link_issues = collect_document_contexts(host_doc)
    elements = []
    skipped_categories = []
    for context in contexts:
        for spec in category_specs:
            try:
                category_elements = collect_category_elements(context, spec)
            except Exception as exc:
                skipped = {
                    "source_document": context.get("source_document"),
                    "source_scope_key": _source_scope_key(context),
                    "category": spec.get("name"),
                    "bic": spec.get("bic"),
                    "reason": to_text(exc),
                }
                skipped_categories.append(skipped)
                link_issues.append({
                    "rule_id": "CATEGORY_COLLECTION_FAILED", "severity": "HIGH",
                    "source_document": context.get("source_document"),
                    "message": "Estimating category collection failed for %s: %s" % (spec.get("name"), to_text(exc)),
                    "values": skipped,
                })
                continue
            if not category_elements:
                continue
            for element in category_elements:
                try:
                    elements.append(extract_element(element, context, spec))
                except Exception as exc:
                    link_issues.append({
                        "rule_id": "ELEMENT_EXTRACTION_FAILED", "severity": "HIGH",
                        "source_document": context.get("source_document"),
                        "message": "Element extraction failed for %s: %s" % (spec.get("name"), to_text(exc)),
                        "values": {"element_id": element_id_value(element.Id), "category": spec.get("name")}
                    })
    elements.sort(key=lambda x: x.get("element_key", ""))
    metadata = model_metadata(host_doc, contexts, app=app)
    metadata["skipped_categories"] = list(skipped_categories)
    return {"elements": elements, "link_issues": link_issues, "model_metadata": metadata, "skipped_categories": skipped_categories, "category_config": config_evidence}
