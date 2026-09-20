from __future__ import absolute_import

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.comparison_export import write_revision_comparison
from revit_estimating.diff import compare_snapshots
from revit_estimating.hashing import sha256_file
from revit_estimating.serialization import read_json, write_json, write_text
from revit_estimating.evidence import comparison_csv_texts
from revit_estimating.validation import validate_comparison_folder, validation_passed


class ComparisonExportTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.baseline_path = os.path.join(ROOT, "tests", "fixtures", "baseline_snapshot.json")
        self.current_path = os.path.join(ROOT, "tests", "fixtures", "current_snapshot.json")
        baseline = read_json(self.baseline_path)
        current = read_json(self.current_path)
        self.result = compare_snapshots(baseline, current)

    def tearDown(self):
        shutil.rmtree(self.root)

    def _write(self, created_at=None):
        return write_revision_comparison(
            self.root,
            self.result,
            baseline_path=self.baseline_path,
            current_path=self.current_path,
            created_at=created_at,
        )

    def test_manifest_hashes_inputs_and_outputs(self):
        folder = self._write()
        manifest = read_json(os.path.join(folder, "comparison_manifest.json"))
        self.assertEqual(manifest["baseline_snapshot"]["sha256"], sha256_file(self.baseline_path))
        self.assertEqual(manifest["current_snapshot"]["sha256"], sha256_file(self.current_path))
        self.assertEqual(manifest["baseline_snapshot"]["status"], "HASHED")
        self.assertEqual(manifest["current_snapshot"]["status"], "HASHED")
        self.assertEqual(manifest["baseline_snapshot"]["package_status"], "STANDALONE_UNVERIFIED")
        self.assertEqual(manifest["current_snapshot"]["package_status"], "STANDALONE_UNVERIFIED")
        for name in ("revision_diff.json", "quantity_deltas.csv", "element_changes.csv"):
            self.assertEqual(manifest["evidence_hashes"][name], sha256_file(os.path.join(folder, name)))

    def test_comparison_validator_passes_clean_package(self):
        folder = self._write()
        findings = validate_comparison_folder(folder)
        self.assertTrue(validation_passed(findings), findings)

    def test_comparison_validator_detects_output_tampering(self):
        folder = self._write()
        path = os.path.join(folder, "quantity_deltas.csv")
        with open(path, "a") as stream:
            stream.write("tampered\n")
        findings = validate_comparison_folder(folder)
        self.assertIn("HASH_MISMATCH", set(item["code"] for item in findings))

    def test_comparison_validator_recomputes_derived_csv_even_if_hash_is_updated(self):
        folder = self._write()
        csv_path = os.path.join(folder, "quantity_deltas.csv")
        with open(csv_path, "a") as stream:
            stream.write("fabricated,row\n")
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        manifest["evidence_hashes"]["quantity_deltas.csv"] = sha256_file(csv_path)
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertNotIn("HASH_MISMATCH", codes)
        self.assertIn("DERIVED_EVIDENCE_MISMATCH", codes)

    def test_comparison_validator_recomputes_result_from_recorded_inputs(self):
        folder = self._write()
        result_path = os.path.join(folder, "revision_diff.json")
        result = read_json(result_path)
        self.assertTrue(result.get("modified"))
        result["modified"][0]["changes"][0]["after"] = "fabricated"
        write_json(result_path, result)

        derived = comparison_csv_texts(result)
        for name, content in derived.items():
            write_text(os.path.join(folder, name), content)

        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        for name in ("revision_diff.json", "quantity_deltas.csv", "element_changes.csv"):
            manifest["evidence_hashes"][name] = sha256_file(os.path.join(folder, name))
        write_json(manifest_path, manifest)

        strict_codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=True))
        relaxed_codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("COMPARISON_RECOMPUTATION_MISMATCH", strict_codes)
        self.assertNotIn("COMPARISON_RECOMPUTATION_MISMATCH", relaxed_codes)

    def test_comparison_validator_reconciles_summary_without_source_inputs(self):
        folder = self._write()
        result_path = os.path.join(folder, "revision_diff.json")
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        result = read_json(result_path)
        manifest = read_json(manifest_path)

        result["summary"]["ADDED"] = result["summary"]["ADDED"] + 5
        manifest["summary"] = dict(result["summary"])
        write_json(result_path, result)
        manifest["evidence_hashes"]["revision_diff.json"] = sha256_file(result_path)
        write_json(manifest_path, manifest)

        codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("COMPARISON_SUMMARY_COUNT_MISMATCH", codes)
        self.assertIn("COMPARISON_CURRENT_TOTAL_MISMATCH", codes)

    def test_comparison_validator_can_skip_original_input_files(self):
        folder = self._write()
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        manifest["baseline_snapshot"]["path"] = os.path.join(self.root, "missing-baseline.json")
        write_json(manifest_path, manifest)
        strict_codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=True))
        relaxed_codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("COMPARISON_INPUT_MISSING", strict_codes)
        self.assertNotIn("COMPARISON_INPUT_MISSING", relaxed_codes)

    def test_skip_input_files_still_validates_input_evidence_structure(self):
        folder = self._write()
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        manifest["baseline_snapshot"]["sha256"] = "not-a-sha256"
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("COMPARISON_INPUT_HASH_INVALID", codes)

    def test_comparison_validator_rejects_status_claim(self):
        folder = self._write()
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        manifest["status"] = "ESTIMATOR_VALIDATED"
        from revit_estimating.serialization import write_json
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("COMPARISON_STATUS_INVALID", codes)

    def test_comparison_validator_reports_malformed_derived_data_without_crashing(self):
        folder = self._write()
        result_path = os.path.join(folder, "revision_diff.json")
        result = read_json(result_path)
        result["quantity_deltas"] = ["not-a-row-object"]
        write_json(result_path, result)
        manifest_path = os.path.join(folder, "comparison_manifest.json")
        manifest = read_json(manifest_path)
        manifest["evidence_hashes"]["revision_diff.json"] = sha256_file(result_path)
        write_json(manifest_path, manifest)
        codes = set(item["code"] for item in validate_comparison_folder(folder, verify_inputs=False))
        self.assertIn("DERIVED_EVIDENCE_RECOMPUTATION_FAILED", codes)

    def test_same_timestamp_creates_versioned_comparison_folder(self):
        created_at = "2026-09-15T12:00:00Z"
        first = self._write(created_at=created_at)
        second = self._write(created_at=created_at)
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith("_v001"))
        self.assertTrue(os.path.isdir(first))
        self.assertTrue(os.path.isdir(second))


if __name__ == "__main__":
    unittest.main()
