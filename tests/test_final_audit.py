from __future__ import absolute_import

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "RevitEstimating.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.diff import compare_snapshots


def _element():
    return {
        "element_key": "HOST:u1",
        "source_scope_key": "HOST",
        "source_document": "Model.rvt",
        "unique_id": "u1",
        "category": "Pipes",
        "family": "Pipe",
        "type": "PVC 300",
        "system": "Storm",
        "material": "PVC",
        "level": "Level 1",
        "mark": "P-1",
        "size": {"diameter_mm": 300.0, "width_mm": None, "height_mm": None, "size_text": "300 mm"},
        "location": {"x_m": 1.0, "y_m": 2.0, "z_m": 0.0},
        "quantities": {"length_m": 10.0, "area_m2": None, "volume_m3": None, "count_ea": 1},
        "primary_quantity_type": "LENGTH",
        "primary_quantity_value": 10.0,
        "primary_quantity_unit": "M",
        "quantity_aggregation_excluded": False,
        "parameters": {"assembly_code": "D20"},
    }


def _snapshot(project_number, project_name="Project A"):
    return {
        "schema_version": "0.1",
        "metadata": {"model": {"project_number": project_number, "project_name": project_name}},
        "elements": [_element()],
        "audit_issues": [],
    }


class FinalAuditTests(unittest.TestCase):
    def test_project_number_mismatch_is_high_warning(self):
        result = compare_snapshots(_snapshot("A-100"), _snapshot("B-200"))
        self.assertEqual(len(result.get("warnings") or []), 1)
        warning = result["warnings"][0]
        self.assertEqual(warning["code"], "PROJECT_NUMBER_MISMATCH")
        self.assertEqual(warning["severity"], "HIGH")

    def test_matching_project_numbers_do_not_warn(self):
        result = compare_snapshots(_snapshot("A-100"), _snapshot("A-100"))
        self.assertEqual(result.get("warnings"), [])

    def test_blank_project_numbers_do_not_create_false_warning(self):
        result = compare_snapshots(_snapshot(""), _snapshot(""))
        self.assertEqual(result.get("warnings"), [])

    def test_project_name_mismatch_is_high_when_numbers_are_blank(self):
        result = compare_snapshots(_snapshot("", "Project A"), _snapshot("", "Project B"))
        self.assertEqual(len(result.get("warnings") or []), 1)
        warning = result["warnings"][0]
        self.assertEqual(warning["code"], "PROJECT_NAME_MISMATCH")
        self.assertEqual(warning["severity"], "HIGH")

    def test_project_name_mismatch_is_medium_when_project_number_matches(self):
        result = compare_snapshots(_snapshot("A-100", "Old Name"), _snapshot("A-100", "New Name"))
        self.assertEqual(len(result.get("warnings") or []), 1)
        warning = result["warnings"][0]
        self.assertEqual(warning["code"], "PROJECT_NAME_MISMATCH")
        self.assertEqual(warning["severity"], "MEDIUM")

    def test_element_extraction_failure_is_high_severity_contract(self):
        path = os.path.join(LIB, "revit_estimating", "revit_adapter.py")
        with open(path, "r") as stream:
            source = stream.read()
        self.assertIn('"rule_id": "ELEMENT_EXTRACTION_FAILED", "severity": "HIGH"', source)

    def test_link_scope_set_change_warns(self):
        baseline = _snapshot("A-100")
        current = _snapshot("A-100")
        baseline["metadata"]["model"]["linked_models"] = [{
            "source_scope_key": "LINK:old",
            "document": "MEP.rvt",
            "document_identity": "C:/models/MEP.rvt",
            "link_instance_name": "MEP : 1",
        }]
        current["metadata"]["model"]["linked_models"] = [{
            "source_scope_key": "LINK:new",
            "document": "MEP.rvt",
            "document_identity": "C:/models/MEP.rvt",
            "link_instance_name": "MEP : 1",
        }]
        warnings = compare_snapshots(baseline, current).get("warnings") or []
        codes = set(item.get("code") for item in warnings)
        self.assertIn("LINK_SCOPE_SET_CHANGED", codes)
        self.assertIn("LINK_INSTANCE_IDENTITY_CHANGED", codes)

    def test_same_link_scope_does_not_warn(self):
        baseline = _snapshot("A-100")
        current = _snapshot("A-100")
        link = {
            "source_scope_key": "LINK:same",
            "document": "MEP.rvt",
            "document_identity": "C:/models/MEP.rvt",
            "link_instance_name": "MEP : 1",
        }
        baseline["metadata"]["model"]["linked_models"] = [dict(link)]
        current["metadata"]["model"]["linked_models"] = [dict(link)]
        codes = set(item.get("code") for item in compare_snapshots(baseline, current).get("warnings") or [])
        self.assertNotIn("LINK_SCOPE_SET_CHANGED", codes)
        self.assertNotIn("LINK_INSTANCE_IDENTITY_CHANGED", codes)

    def test_linked_location_fails_closed_without_transform(self):
        path = os.path.join(LIB, "revit_estimating", "revit_adapter.py")
        with open(path, "r") as stream:
            source = stream.read()
        self.assertIn('"location": None if context.get("is_linked") and context.get("transform") is None', source)
        self.assertIn("except Exception:\n            return None\n    return {\"x_m\"", source)

    def test_link_scope_fallback_uses_instance_id_before_name(self):
        path = os.path.join(LIB, "revit_estimating", "revit_adapter.py")
        with open(path, "r") as stream:
            source = stream.read()
        id_pos = source.index('return "LINK:ID:%s"')
        name_pos = source.index('return "LINK:NAME:%s"')
        self.assertLess(id_pos, name_pos)


if __name__ == "__main__":
    unittest.main()
