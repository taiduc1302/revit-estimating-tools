from __future__ import absolute_import

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")

BUTTON_DIRS = [
    os.path.join(EXTENSION, "Estimating.tab", "Model.panel", "Model Audit.pushbutton"),
    os.path.join(EXTENSION, "Estimating.tab", "Model.panel", "Extract Snapshot.pushbutton"),
    os.path.join(EXTENSION, "Estimating.tab", "Changes.panel", "Compare Revision.pushbutton"),
    os.path.join(EXTENSION, "Estimating.tab", "Export.panel", "Estimating Package.pushbutton"),
]
BUTTON_SCRIPTS = [os.path.join(path, "script.py") for path in BUTTON_DIRS]


class ExtensionContractTests(unittest.TestCase):
    def test_extension_manifest_exists(self):
        path = os.path.join(EXTENSION, "extension.json")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r") as stream:
            data = json.load(stream)
        self.assertEqual(data.get("name"), "Revit Estimating Tools")

    def test_legacy_extension_yaml_is_absent(self):
        self.assertFalse(os.path.exists(os.path.join(EXTENSION, "extension.yaml")))

    def test_expected_buttons_exist(self):
        for path in BUTTON_SCRIPTS:
            self.assertTrue(os.path.isfile(path), path)

    def test_v01_button_scripts_do_not_start_transactions(self):
        forbidden = ("DB.Transaction(", "TransactionGroup(", "SubTransaction(")
        for path in BUTTON_SCRIPTS:
            with open(path, "r") as stream:
                content = stream.read()
            for token in forbidden:
                self.assertNotIn(token, content, "%s contains %s" % (path, token))

    def test_buttons_remain_default_ironpython_while_using_pyrevit_forms(self):
        for path in BUTTON_SCRIPTS:
            with open(path, "r") as stream:
                first_line = stream.readline().strip().lower()
            self.assertNotIn("python3", first_line, path)

    def test_bundle_metadata_keeps_clean_engine_and_minimum_revit(self):
        for button_dir in BUTTON_DIRS:
            path = os.path.join(button_dir, "bundle.yaml")
            self.assertTrue(os.path.isfile(path), path)
            with open(path, "r") as stream:
                content = stream.read().lower()
            self.assertIn("min_revit_version: 2021", content, path)
            self.assertIn("engine:", content, path)
            self.assertIn("clean: true", content, path)

    def test_no_company_specific_name(self):
        forbidden = "tybo"
        checked = []
        for base in (EXTENSION, os.path.join(ROOT, "lib"), os.path.join(ROOT, "docs"), os.path.join(ROOT, "config"), os.path.join(ROOT, "tools")):
            for dirpath, _, filenames in os.walk(base):
                for filename in filenames:
                    if not filename.lower().endswith((".py", ".md", ".json", ".yaml", ".yml")):
                        continue
                    path = os.path.join(dirpath, filename)
                    checked.append(path)
                    with open(path, "r") as stream:
                        content = stream.read().lower()
                    self.assertNotIn(forbidden, content, path)
        self.assertTrue(checked)


if __name__ == "__main__":
    unittest.main()
