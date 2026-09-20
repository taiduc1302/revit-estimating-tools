from __future__ import absolute_import

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")
LIB = os.path.join(EXTENSION, "lib")
CLI = os.path.join(ROOT, "tools", "revit_estimating.py")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating.doctor import run_doctor
from revit_estimating.hashing import sha256_file
from revit_estimating.validation import validation_passed


class InstallabilityTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def _copy_extension(self):
        target = os.path.join(self.root, "RevitEstimating.extension")
        shutil.copytree(EXTENSION, target)
        return target

    def test_standalone_extension_passes_doctor(self):
        target = self._copy_extension()
        findings = run_doctor(target)
        self.assertTrue(validation_passed(findings), findings)

    def test_extension_without_required_suffix_fails_doctor(self):
        target = os.path.join(self.root, "RevitEstimating")
        shutil.copytree(EXTENSION, target)
        codes = set(item.get("code") for item in run_doctor(target))
        self.assertIn("EXTENSION_SUFFIX_INVALID", codes)

    def test_double_nested_extension_fails_at_outer_folder(self):
        outer = os.path.join(self.root, "RevitEstimating.extension")
        inner = os.path.join(outer, "RevitEstimating.extension")
        os.makedirs(outer)
        shutil.copytree(EXTENSION, inner)
        codes = set(item.get("code") for item in run_doctor(outer))
        self.assertIn("EXTENSION_MANIFEST_MISSING", codes)
        self.assertIn("EXTENSION_RUNTIME_MISSING", codes)

    def test_standalone_runtime_loads_embedded_category_config(self):
        target = self._copy_extension()
        copied_lib = os.path.join(target, "lib")
        code = (
            "import sys; "
            "sys.path.insert(0, %r); "
            "from revit_estimating.config import load_category_specs, category_config_path; "
            "specs=load_category_specs(force_reload=True); "
            "assert len(specs) > 0; "
            "assert category_config_path().startswith(%r); "
            "print(len(specs))"
        ) % (copied_lib, target)
        output = subprocess.check_output([sys.executable, "-c", code], cwd=self.root)
        self.assertTrue(output.strip())

    def test_extension_zip_is_deterministic_and_self_contained(self):
        first = os.path.join(self.root, "first.zip")
        second = os.path.join(self.root, "second.zip")
        for output_path in (first, second):
            raw = subprocess.check_output([
                sys.executable, CLI, "build-extension", "--output", output_path, "--json"
            ], cwd=ROOT)
            payload = json.loads(raw.decode("utf-8"))
            self.assertTrue(payload.get("passed"), payload)
            self.assertTrue(os.path.isfile(output_path))

        self.assertEqual(sha256_file(first), sha256_file(second))
        with zipfile.ZipFile(first, "r") as archive:
            names = set(archive.namelist())
        prefix = "RevitEstimating.extension/"
        self.assertTrue(names)
        self.assertTrue(all(name.startswith(prefix) for name in names))
        self.assertIn(prefix + "extension.json", names)
        self.assertIn(prefix + "lib/revit_estimating/__init__.py", names)
        self.assertIn(prefix + "config/categories.json", names)
        self.assertFalse(any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names))


if __name__ == "__main__":
    unittest.main()
