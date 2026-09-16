from __future__ import absolute_import

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
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


def _snapshot(project_number):
    return {
        "schema_version": "0.1",
        "metadata": {"model": {"project_number": project_number}},
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


if __name__ == "__main__":
    unittest.main()
