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
from revit_estimating.serialization import read_json


class ComparisonExportTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.baseline_path = os.path.join(ROOT, "tests", "fixtures", "baseline_snapshot.json")
        self.current_path = os.path.join(ROOT, "tests", "fixtures", "current_snapshot.json")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_manifest_hashes_inputs_and_outputs(self):
        baseline = read_json(self.baseline_path)
        current = read_json(self.current_path)
        result = compare_snapshots(baseline, current)
        folder = write_revision_comparison(
            self.root,
            result,
            baseline_path=self.baseline_path,
            current_path=self.current_path,
        )
        manifest = read_json(os.path.join(folder, "comparison_manifest.json"))
        self.assertEqual(manifest["baseline_snapshot"]["sha256"], sha256_file(self.baseline_path))
        self.assertEqual(manifest["current_snapshot"]["sha256"], sha256_file(self.current_path))
        self.assertEqual(manifest["baseline_snapshot"]["status"], "HASHED")
        self.assertEqual(manifest["current_snapshot"]["status"], "HASHED")
        for name in ("revision_diff.json", "quantity_deltas.csv", "element_changes.csv"):
            self.assertEqual(manifest["evidence_hashes"][name], sha256_file(os.path.join(folder, name)))


if __name__ == "__main__":
    unittest.main()
