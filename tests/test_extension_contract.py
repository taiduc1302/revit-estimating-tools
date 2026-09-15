from __future__ import absolute_import

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")

BUTTON_SCRIPTS = [
    os.path.join(EXTENSION, "Estimating.tab", "Model.panel", "Model Audit.pushbutton", "script.py"),
    os.path.join(EXTENSION, "Estimating.tab", "Model.panel", "Extract Snapshot.pushbutton", "script.py"),
    os.path.join(EXTENSION, "Estimating.tab", "Changes.panel", "Compare Revision.pushbutton", "script.py"),
    os.path.join(EXTENSION, "Estimating.tab", "Export.panel", "Estimating Package.pushbutton", "script.py"),
]


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

    def test_no_company_specific_name(self):
        forbidden = "tybo"
        checked = []
        for base in (EXTENSION, os.path.join(ROOT, "lib"), os.path.join(ROOT, "docs"), os.path.join(ROOT, "config")):
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
