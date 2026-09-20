from __future__ import absolute_import

import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")
LIB = os.path.join(EXTENSION, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from revit_estimating import __version__


class ReleaseContractTests(unittest.TestCase):
    def test_runtime_version_matches_unreleased_changelog_entry(self):
        path = os.path.join(ROOT, "CHANGELOG.md")
        with open(path, "r") as stream:
            changelog = stream.read()
        self.assertIn("## %s - Unreleased" % __version__, changelog)

    def test_offline_build_cannot_claim_production_ready(self):
        audit_path = os.path.join(ROOT, "docs", "FINAL_AUDIT.md")
        checklist_path = os.path.join(ROOT, "docs", "RELEASE_CHECKLIST.md")
        with open(audit_path, "r") as stream:
            audit = stream.read()
        with open(checklist_path, "r") as stream:
            checklist = stream.read()
        self.assertRegex(audit, r"LIVE_REVIT_VALIDATED[^\n]*false")
        self.assertRegex(audit, r"PRODUCTION_READY[^\n]*false")
        self.assertIn("Release tag permitted: no", checklist)

    def test_release_checklist_requires_live_revit_gate(self):
        path = os.path.join(ROOT, "docs", "RELEASE_CHECKLIST.md")
        with open(path, "r") as stream:
            content = stream.read()
        required = (
            "pyRevit loads the extension",
            "No command dirties or modifies the Revit model",
            "Category-level quantities reconcile",
            "deployment ZIP SHA-256",
        )
        for text in required:
            self.assertIn(text, content)


if __name__ == "__main__":
    unittest.main()
