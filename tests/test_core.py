from __future__ import absolute_import

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.aggregation import aggregate_primary_quantities, quantity_delta
from revit_estimating.audit import audit_element
from revit_estimating.diff import compare_snapshots
from revit_estimating.hashing import sha256_text
from revit_estimating.normalization import length_ft_to_m, area_sqft_to_sqm, volume_cuft_to_cum
from revit_estimating.package import create_estimating_package
from revit_estimating.serialization import canonical_json
from revit_estimating.snapshot import write_snapshot_package
from revit_estimating.manifest import build_manifest


def element(key="doc:u1", unique_id="u1", length=10.0, material="PVC", mark="P-1", location=None):
    return {
        "element_key": key,
        "source_document": "Model.rvt",
        "source_document_id": "doc",
        "is_linked": False,
        "element_id": 1,
        "unique_id": unique_id,
        "category": "Pipes",
        "family": "Pipe",
        "type": "PVC 300",
        "system": "Storm",
        "material": material,
        "level": "Level 1",
        "workset": None,
        "phase_created": "New Construction",
        "phase_demolished": None,
        "design_option": None,
        "mark": mark,
        "size": {"diameter_mm": 300.0, "width_mm": None, "height_mm": None, "size_text": "300 mm"},
        "location": location or {"x_m": 1.0, "y_m": 2.0, "z_m": 0.0},
        "quantities": {"length_m": length, "area_m2": None, "volume_m3": None, "count_ea": 1},
        "primary_quantity_type": "LENGTH",
        "primary_quantity_value": length,
        "primary_quantity_unit": "M",
        "fingerprints": {},
    }


class NormalizationTests(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(length_ft_to_m(1.0), 0.3048)

    def test_area(self):
        self.assertEqual(area_sqft_to_sqm(10.0), 0.92903)

    def test_volume(self):
        self.assertAlmostEqual(volume_cuft_to_cum(10.0), 0.283168)


class AuditTests(unittest.TestCase):
    def test_missing_pipe_data_is_flagged(self):
        row = element()
        row["material"] = None
        row["system"] = None
        row["size"] = {}
        rules = set(x["rule_id"] for x in audit_element(row))
        self.assertIn("MISSING_MATERIAL", rules)
        self.assertIn("MISSING_SYSTEM", rules)
        self.assertIn("MISSING_SIZE", rules)


class AggregationTests(unittest.TestCase):
    def test_aggregation(self):
        rows = aggregate_primary_quantities([element(length=10), element(key="doc:u2", unique_id="u2", length=12)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 22.0)
        self.assertEqual(rows[0]["element_count"], 2)

    def test_quantity_delta(self):
        rows = quantity_delta([element(length=10)], [element(length=13)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["delta"], 3.0)


class DiffTests(unittest.TestCase):
    def test_modified_exact_identity(self):
        before = element(length=10)
        after = element(length=12)
        result = compare_snapshots({"elements": [before]}, {"elements": [after]})
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        self.assertEqual(result["summary"]["ADDED"], 0)

    def test_possible_recreated(self):
        before = element(key="doc:old", unique_id="old", length=10)
        after = element(key="doc:new", unique_id="new", length=10)
        result = compare_snapshots({"elements": [before]}, {"elements": [after]})
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 1)
        self.assertEqual(result["summary"]["ADDED"], 0)
        self.assertEqual(result["summary"]["REMOVED"], 0)

    def test_different_category_not_recreated(self):
        before = element(key="doc:old", unique_id="old")
        after = element(key="doc:new", unique_id="new")
        after["category"] = "Ducts"
        result = compare_snapshots({"elements": [before]}, {"elements": [after]})
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 0)
        self.assertEqual(result["summary"]["ADDED"], 1)
        self.assertEqual(result["summary"]["REMOVED"], 1)


class SerializationTests(unittest.TestCase):
    def test_canonical_json_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_hash_stable(self):
        self.assertEqual(sha256_text("abc"), sha256_text("abc"))


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_snapshot_and_zip(self):
        rows = [element()]
        manifest = build_manifest("Test", {"host_document": "Model.rvt"}, 1, 0, created_at="2026-09-15T00:00:00Z")
        folder = write_snapshot_package(self.root, manifest, rows, [])
        self.assertTrue(os.path.isfile(os.path.join(folder, "manifest.json")))
        with open(os.path.join(folder, "manifest.json"), "r") as stream:
            saved = json.load(stream)
        self.assertEqual(saved["status"], "NOT_ESTIMATOR_VALIDATED")
        self.assertIn("raw_snapshot.json", saved["evidence_hashes"])
        zip_path = create_estimating_package(folder)
        self.assertTrue(os.path.isfile(zip_path))


if __name__ == "__main__":
    unittest.main()
