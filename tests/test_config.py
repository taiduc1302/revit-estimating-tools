from __future__ import absolute_import

import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "RevitEstimating.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating import config
from revit_estimating.hashing import sha256_file


class CategoryConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_path = config.category_config_path
        self.temp_paths = []

    def tearDown(self):
        config.category_config_path = self.original_path
        config.load_category_specs(force_reload=True)
        for path in self.temp_paths:
            try:
                os.remove(path)
            except OSError:
                pass

    def _temp_file(self, content):
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        with io.open(path, "w", encoding="utf-8") as stream:
            stream.write(content)
        self.temp_paths.append(path)
        return path

    def _point_to(self, path):
        config.category_config_path = lambda: path

    def test_repository_config_is_cached_and_hashed(self):
        first = config.load_category_specs(force_reload=True)
        second = config.load_category_specs()
        self.assertIs(first, second)
        evidence = config.category_config_evidence()
        self.assertEqual(evidence["sha256"], sha256_file(self.original_path()))
        self.assertEqual(evidence["category_count"], len(first))
        self.assertEqual(evidence["mode"], "REQUIRED_FAIL_CLOSED")

    def test_missing_config_fails_closed(self):
        path = os.path.join(tempfile.gettempdir(), "missing-revit-estimating-categories.json")
        try:
            os.remove(path)
        except OSError:
            pass
        self._point_to(path)
        with self.assertRaises(ValueError):
            config.load_category_specs(force_reload=True)

    def test_malformed_config_fails_closed(self):
        path = self._temp_file("{not-json")
        self._point_to(path)
        with self.assertRaises(ValueError):
            config.load_category_specs(force_reload=True)

    def test_schema_mismatch_fails_closed(self):
        path = self._temp_file(json.dumps({"schema_version": "99", "categories": []}))
        self._point_to(path)
        with self.assertRaises(ValueError):
            config.load_category_specs(force_reload=True)

    def test_duplicate_mapping_fails_closed(self):
        payload = {
            "schema_version": "0.1",
            "categories": [
                {"name": "A", "bic": "OST_Walls", "primary_quantity": "AREA"},
                {"name": "B", "bic": "OST_Walls", "primary_quantity": "AREA"},
            ],
        }
        path = self._temp_file(json.dumps(payload))
        self._point_to(path)
        with self.assertRaises(ValueError):
            config.load_category_specs(force_reload=True)


if __name__ == "__main__":
    unittest.main()
