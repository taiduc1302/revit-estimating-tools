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
from revit_estimating.audit import audit_element, audit_model
from revit_estimating.diff import compare_snapshots
from revit_estimating.config import category_config_evidence
from revit_estimating.fingerprint import similarity_score
from revit_estimating.hashing import sha256_text, sha256_file
from revit_estimating.logging_utils import write_run_log
from revit_estimating.normalization import length_ft_to_m, area_sqft_to_sqm, volume_cuft_to_cum
from revit_estimating.package import create_estimating_package
from revit_estimating.serialization import canonical_json, read_json, write_json, write_csv
from revit_estimating.snapshot import write_snapshot_package
from revit_estimating.manifest import build_manifest
from revit_estimating.validation import validate_snapshot_folder, validate_snapshot_input_file, validation_passed


def element(key="HOST:u1", unique_id="u1", length=10.0, material="PVC", mark="P-1", location=None,
            source_document="Model.rvt", source_scope_key="HOST", is_linked=False, link_uid=None):
    return {
        "element_key": key, "source_scope_key": source_scope_key, "source_document": source_document,
        "source_document_id": "doc", "is_linked": is_linked, "link_instance_unique_id": link_uid,
        "element_id": 1, "unique_id": unique_id, "category": "Pipes", "family": "Pipe",
        "type": "PVC 300", "system": "Storm", "material": material, "level": "Level 1",
        "workset": None, "phase_created": "New Construction", "phase_demolished": None,
        "design_option": None, "mark": mark,
        "size": {"diameter_mm": 300.0, "width_mm": None, "height_mm": None, "size_text": "300 mm"},
        "location": location or {"x_m": 1.0, "y_m": 2.0, "z_m": 0.0},
        "quantities": {"length_m": length, "area_m2": None, "volume_m3": None, "count_ea": 1},
        "primary_quantity_type": "LENGTH", "primary_quantity_value": length,
        "primary_quantity_unit": "M", "quantity_aggregation_excluded": False,
        "parameters": {
            "description": "Storm pipe", "comments": None, "type_comments": None,
            "assembly_code": "D20", "keynote": None, "model": None,
        },
        "fingerprints": {},
    }


def snapshot(elements, schema_version="0.1"):
    return {"schema_version": schema_version, "metadata": {}, "elements": elements, "audit_issues": []}


class NormalizationTests(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(length_ft_to_m(1.0), 0.3048)

    def test_area(self):
        self.assertEqual(area_sqft_to_sqm(10.0), 0.92903)

    def test_volume(self):
        self.assertAlmostEqual(volume_cuft_to_cum(10.0), 0.283168)


class AuditTests(unittest.TestCase):
    def test_link_issue_ids_include_trace_values(self):
        issues = audit_model([], [
            {"rule_id": "LINK_UNLOADED", "severity": "HIGH", "source_document": "Host.rvt", "message": "Link unavailable", "values": {"link_instance_id": 10}},
            {"rule_id": "LINK_UNLOADED", "severity": "HIGH", "source_document": "Host.rvt", "message": "Link unavailable", "values": {"link_instance_id": 20}},
        ])
        self.assertEqual(len(issues), 2)
        self.assertNotEqual(issues[0]["issue_id"], issues[1]["issue_id"])

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
        rows = aggregate_primary_quantities([element(length=10), element(key="HOST:u2", unique_id="u2", length=12)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 22.0)
        self.assertEqual(rows[0]["element_count"], 2)

    def test_aggregation_ignores_size_display_text_when_numeric_size_matches(self):
        first = element(length=10)
        second = element(key="HOST:u2", unique_id="u2", length=12)
        second["size"]["size_text"] = "0.30 m"
        rows = aggregate_primary_quantities([first, second])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 22.0)

    def test_audit_only_element_is_not_aggregated(self):
        row = element()
        row["quantity_aggregation_excluded"] = True
        self.assertEqual(aggregate_primary_quantities([row]), [])
        self.assertEqual(quantity_delta([row], [row]), [])

    def test_quantity_delta(self):
        rows = quantity_delta([element(length=10)], [element(length=13)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["delta"], 3.0)

    def test_quantity_delta_survives_document_rename(self):
        before = element(length=10, source_document="Model_A.rvt")
        after = element(length=13, source_document="Model_B.rvt")
        rows = quantity_delta([before], [after])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["delta"], 3.0)
        self.assertEqual(rows[0]["baseline_source_document"], "Model_A.rvt")
        self.assertEqual(rows[0]["current_source_document"], "Model_B.rvt")

    def test_non_positive_quantities_do_not_reduce_aggregated_totals(self):
        positive = element(length=10)
        negative = element(key="HOST:u2", unique_id="u2", length=-4)
        zero = element(key="HOST:u3", unique_id="u3", length=0)
        rows = aggregate_primary_quantities([positive, negative, zero])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 10.0)
        delta_rows = quantity_delta([positive], [positive, negative, zero])
        self.assertEqual(len(delta_rows), 1)
        self.assertEqual(delta_rows[0]["delta"], 0.0)


class DiffTests(unittest.TestCase):
    def test_modified_exact_identity(self):
        result = compare_snapshots(snapshot([element(length=10)]), snapshot([element(length=12)]))
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        self.assertEqual(result["summary"]["ADDED"], 0)

    def test_location_change_is_semantic_change(self):
        before = element(location={"x_m": 1.0, "y_m": 2.0, "z_m": 0.0})
        after = element(location={"x_m": 2.0, "y_m": 2.0, "z_m": 0.0})
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        fields = [item.get("field") for item in result["modified"][0]["changes"]]
        self.assertIn("location.x_m", fields)

    def test_estimating_parameter_change_is_semantic_change(self):
        before = element()
        after = element()
        after["parameters"]["assembly_code"] = "D30"
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        fields = [item.get("field") for item in result["modified"][0]["changes"]]
        self.assertIn("parameters.assembly_code", fields)

    def test_display_size_text_change_is_not_semantic_change(self):
        before = element()
        after = element()
        after["size"]["size_text"] = "0.30 m"
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["MODIFIED"], 0)
        self.assertEqual(result["summary"]["UNCHANGED"], 1)

    def test_numeric_size_change_is_semantic_change(self):
        before = element()
        after = element()
        after["size"]["diameter_mm"] = 375.0
        after["size"]["size_text"] = "375 mm"
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        fields = [item.get("field") for item in result["modified"][0]["changes"]]
        self.assertIn("size", fields)

    def test_exact_identity_survives_document_rename(self):
        before = element(length=10, source_document="Before.rvt")
        after = element(length=12, source_document="After.rvt")
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        self.assertEqual(result["summary"]["ADDED"], 0)
        self.assertEqual(result["summary"]["REMOVED"], 0)

    def test_possible_recreated(self):
        before = element(key="HOST:old", unique_id="old", length=10)
        after = element(key="HOST:new", unique_id="new", length=10)
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 1)
        self.assertEqual(result["summary"]["ADDED"], 0)
        self.assertEqual(result["summary"]["REMOVED"], 0)

    def test_different_category_not_recreated(self):
        before = element(key="HOST:old", unique_id="old")
        after = element(key="HOST:new", unique_id="new")
        after["category"] = "Ducts"
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 0)
        self.assertEqual(result["summary"]["ADDED"], 1)
        self.assertEqual(result["summary"]["REMOVED"], 1)

    def test_recreated_match_does_not_cross_link_instances(self):
        before = element(key="LINK:A:old", unique_id="old", source_scope_key="LINK:A", is_linked=True, link_uid="A")
        after = element(key="LINK:B:new", unique_id="new", source_scope_key="LINK:B", is_linked=True, link_uid="B")
        self.assertEqual(similarity_score(before, after), 0.0)
        result = compare_snapshots(snapshot([before]), snapshot([after]))
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 0)

    def test_recreated_matching_uses_reciprocal_best_candidate(self):
        old_a = element(key="HOST:a", unique_id="a", mark="A")
        old_b = element(key="HOST:b", unique_id="b", mark="B")
        new_b = element(key="HOST:new", unique_id="new", mark="B")
        result = compare_snapshots(snapshot([old_a, old_b]), snapshot([new_b]))
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 1)
        self.assertEqual(result["possible_recreated"][0]["baseline_element_key"], "HOST:b")
        self.assertEqual(result["possible_recreated"][0]["current_element_key"], "HOST:new")
        self.assertEqual(result["summary"]["REMOVED"], 1)
        self.assertEqual(result["removed"][0]["element_key"], "HOST:a")

    def test_duplicate_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_snapshots(snapshot([element(), element(length=12)]), snapshot([element(key="HOST:u2", unique_id="u2")]))

    def test_unsupported_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_snapshots(snapshot([element()]), snapshot([element()], schema_version="0.2"))

    def test_missing_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_snapshots({"elements": [element()]}, snapshot([element()]))


class GoldenFixtureTests(unittest.TestCase):
    def test_golden_revision_comparison(self):
        baseline = read_json(os.path.join(ROOT, "tests", "fixtures", "baseline_snapshot.json"))
        current = read_json(os.path.join(ROOT, "tests", "fixtures", "current_snapshot.json"))
        result = compare_snapshots(baseline, current)
        self.assertEqual(result["summary"]["ADDED"], 1)
        self.assertEqual(result["summary"]["REMOVED"], 1)
        self.assertEqual(result["summary"]["MODIFIED"], 1)
        self.assertEqual(result["summary"]["POSSIBLE_RECREATED"], 0)
        self.assertEqual(result["summary"]["UNCHANGED"], 1)
        deltas = dict(((row.get("category"), row.get("type")), row.get("delta")) for row in result["quantity_deltas"])
        self.assertEqual(deltas[("Pipes", "PVC 300")], 2.0)
        self.assertEqual(deltas[("Walls", "Concrete 200")], -20.0)
        self.assertEqual(deltas[("Floors", "Concrete Slab")], 30.0)
        self.assertEqual(deltas[("Conduits", "EMT 50")], 0.0)


class SerializationTests(unittest.TestCase):
    def test_canonical_json_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_hash_stable(self):
        self.assertEqual(sha256_text("abc"), sha256_text("abc"))

    def test_canonical_json_rejects_non_finite_numbers(self):
        with self.assertRaises(ValueError):
            canonical_json({"value": float("nan")})

    def test_read_json_rejects_non_finite_numbers(self):
        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "bad.json")
            with open(path, "w") as stream:
                stream.write('{"value": NaN}')
            with self.assertRaises(ValueError):
                read_json(path)
        finally:
            shutil.rmtree(root)

    def test_csv_escapes_formula_like_text_but_preserves_numeric_values(self):
        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "safe.csv")
            write_csv(path, [
                {"text": "=HYPERLINK(\"https://example.invalid\")", "number": -2.5},
                {"text": "  +SUM(1,2)", "number": 3.0},
            ], ["text", "number"])
            with open(path, "r") as stream:
                content = stream.read()
            self.assertIn("'=HYPERLINK", content)
            self.assertIn("'  +SUM", content)
            self.assertIn("-2.5", content)
            self.assertNotIn("'-2.5", content)
        finally:
            shutil.rmtree(root)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def _build_snapshot(self):
        manifest = build_manifest("Test", {"host_document": "Model.rvt"}, 1, 0, extraction_config={"categories": category_config_evidence(force_reload=True), "read_only": True}, created_at="2026-09-15T00:00:00Z")
        return write_snapshot_package(self.root, manifest, [element()], [])

    def test_snapshot_and_zip(self):
        folder = self._build_snapshot()
        self.assertTrue(os.path.isfile(os.path.join(folder, "manifest.json")))
        with open(os.path.join(folder, "manifest.json"), "r") as stream:
            saved = json.load(stream)
        self.assertEqual(saved["status"], "NOT_ESTIMATOR_VALIDATED")
        self.assertIn("raw_snapshot.json", saved["evidence_hashes"])
        self.assertTrue(os.path.isfile(create_estimating_package(folder)))

    def test_elements_csv_includes_estimating_metadata(self):
        folder = self._build_snapshot()
        with open(os.path.join(folder, "elements.csv"), "r") as stream:
            header = stream.readline()
        self.assertIn("parameters", header)
        self.assertIn("quantity_aggregation_excluded", header)

    def test_snapshot_validator_passes_clean_package(self):
        folder = self._build_snapshot()
        findings = validate_snapshot_folder(folder)
        self.assertTrue(validation_passed(findings), findings)

    def test_snapshot_records_category_config_provenance(self):
        folder = self._build_snapshot()
        manifest = read_json(os.path.join(folder, "manifest.json"))
        categories = manifest.get("extraction_config", {}).get("categories", {})
        self.assertEqual(categories.get("mode"), "REQUIRED_FAIL_CLOSED")
        self.assertEqual(len(categories.get("sha256") or ""), 64)
        self.assertGreater(categories.get("category_count", 0), 0)

    def test_snapshot_validator_requires_category_config_provenance(self):
        folder = self._build_snapshot()
        manifest_path = os.path.join(folder, "manifest.json")
        manifest = read_json(manifest_path)
        manifest["extraction_config"] = {}
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_snapshot_folder(folder))
        self.assertIn("CATEGORY_CONFIG_EVIDENCE_MISSING", codes)

    def test_run_log_is_hashed_and_tampering_blocks_packaging(self):
        folder = self._build_snapshot()
        write_run_log(folder, {"command": "test", "status": "ok"})
        manifest = read_json(os.path.join(folder, "manifest.json"))
        self.assertIn("run_log.json", manifest.get("evidence_hashes") or {})
        self.assertTrue(validation_passed(validate_snapshot_folder(folder)))
        with open(os.path.join(folder, "run_log.json"), "a") as stream:
            stream.write("tampered\n")
        findings = validate_snapshot_folder(folder)
        self.assertIn("HASH_MISMATCH", set(item["code"] for item in findings))
        with self.assertRaises(ValueError):
            create_estimating_package(folder)

    def test_snapshot_input_requires_intact_package(self):
        folder = self._build_snapshot()
        raw_path = os.path.join(folder, "raw_snapshot.json")
        self.assertTrue(validation_passed(validate_snapshot_input_file(raw_path)))
        standalone = os.path.join(ROOT, "tests", "fixtures", "baseline_snapshot.json")
        strict_codes = set(item["code"] for item in validate_snapshot_input_file(standalone))
        self.assertIn("SNAPSHOT_PACKAGE_REQUIRED", strict_codes)
        self.assertTrue(validation_passed(validate_snapshot_input_file(standalone, allow_standalone=True)))

    def test_snapshot_input_rejects_tampered_package(self):
        folder = self._build_snapshot()
        raw_path = os.path.join(folder, "raw_snapshot.json")
        with open(raw_path, "a") as stream:
            stream.write("tampered\n")
        codes = set(item["code"] for item in validate_snapshot_input_file(raw_path))
        self.assertTrue("HASH_MISMATCH" in codes or "SNAPSHOT_INVALID" in codes)

    def test_snapshot_validator_detects_tampering(self):
        folder = self._build_snapshot()
        path = os.path.join(folder, "elements.csv")
        with open(path, "a") as stream:
            stream.write("tampered\n")
        findings = validate_snapshot_folder(folder)
        self.assertIn("HASH_MISMATCH", set(item["code"] for item in findings))

    def test_snapshot_validator_recomputes_derived_csv_even_if_hash_is_updated(self):
        folder = self._build_snapshot()
        csv_path = os.path.join(folder, "elements.csv")
        with open(csv_path, "a") as stream:
            stream.write("fabricated,row\n")
        manifest_path = os.path.join(folder, "manifest.json")
        manifest = read_json(manifest_path)
        manifest["evidence_hashes"]["elements.csv"] = sha256_file(csv_path)
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_snapshot_folder(folder))
        self.assertNotIn("HASH_MISMATCH", codes)
        self.assertIn("DERIVED_EVIDENCE_MISMATCH", codes)

    def test_package_output_cannot_overwrite_snapshot_evidence(self):
        folder = self._build_snapshot()
        manifest_path = os.path.join(folder, "manifest.json")
        with self.assertRaises(ValueError):
            create_estimating_package(folder, output_path=manifest_path)
        saved = read_json(manifest_path)
        self.assertEqual(saved["status"], "NOT_ESTIMATOR_VALIDATED")

    def test_snapshot_validator_detects_duplicate_identity(self):
        folder = self._build_snapshot()
        path = os.path.join(folder, "raw_snapshot.json")
        data = read_json(path)
        data["elements"].append(dict(data["elements"][0]))
        write_json(path, data)
        findings = validate_snapshot_folder(folder)
        self.assertIn("ELEMENT_KEY_DUPLICATE", set(item["code"] for item in findings))

    def test_snapshot_validator_reports_malformed_element_without_crashing(self):
        folder = self._build_snapshot()
        raw_path = os.path.join(folder, "raw_snapshot.json")
        data = read_json(raw_path)
        data["elements"][0] = "not-an-element-object"
        write_json(raw_path, data)
        manifest_path = os.path.join(folder, "manifest.json")
        manifest = read_json(manifest_path)
        manifest["evidence_hashes"]["raw_snapshot.json"] = sha256_file(raw_path)
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_snapshot_folder(folder))
        self.assertIn("DERIVED_EVIDENCE_RECOMPUTATION_FAILED", codes)
        self.assertIn("ELEMENT_INVALID", codes)

    def test_snapshot_validator_detects_unsupported_schema(self):
        folder = self._build_snapshot()
        path = os.path.join(folder, "raw_snapshot.json")
        data = read_json(path)
        data["schema_version"] = "0.2"
        write_json(path, data)
        codes = set(item["code"] for item in validate_snapshot_folder(folder))
        self.assertIn("SCHEMA_VERSION_UNSUPPORTED", codes)
        self.assertIn("SCHEMA_VERSION_MISMATCH", codes)

    def test_snapshot_validator_rejects_unvalidated_status_claim_divergence(self):
        folder = self._build_snapshot()
        manifest_path = os.path.join(folder, "manifest.json")
        manifest = read_json(manifest_path)
        manifest["status"] = "ESTIMATOR_VALIDATED"
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_snapshot_folder(folder))
        self.assertIn("STATUS_INVALID", codes)
        self.assertIn("MANIFEST_METADATA_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
