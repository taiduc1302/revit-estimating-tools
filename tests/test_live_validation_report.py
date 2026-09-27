from __future__ import absolute_import

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "tools", "revit_estimating.py")
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")


class LiveValidationReportTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.report = os.path.join(self.root, "live.json")

    def tearDown(self):
        shutil.rmtree(self.root)

    def _create(self):
        raw = subprocess.check_output([
            sys.executable, CLI, "live-validation-template",
            "--extension", EXTENSION,
            "--output", self.report,
            "--commit", "abc123",
            "--workflow-run", "999",
            "--artifact-id", "12345",
            "--zip-sha256", "f" * 64,
            "--json",
        ], cwd=ROOT)
        payload = json.loads(raw.decode("utf-8"))
        self.assertTrue(payload.get("passed"), payload)
        return json.load(open(self.report, "r"))

    def test_template_records_deployment_identity_and_stays_unvalidated(self):
        data = self._create()
        self.assertEqual(data["status"], "LIVE_VALIDATION_INCOMPLETE")
        self.assertEqual(data["deployment"]["source_commit"], "abc123")
        self.assertEqual(data["deployment"]["workflow_run"], "999")
        self.assertEqual(data["deployment"]["artifact_id"], "12345")
        self.assertEqual(data["deployment"]["deployment_zip_sha256"], "f" * 64)
        self.assertFalse(data["final"]["live_revit_validated"])
        self.assertFalse(data["final"]["production_ready"])
        self.assertTrue(data["checks"])
        self.assertTrue(all(item["status"] == "PENDING" for item in data["checks"]))

    def test_incomplete_template_is_structurally_valid(self):
        self._create()
        code = subprocess.call([
            sys.executable, CLI, "validate-live-report", self.report, "--json"
        ], cwd=ROOT)
        self.assertEqual(code, 0)

    def test_cannot_claim_live_validation_with_pending_checks(self):
        data = self._create()
        data["final"]["live_revit_validated"] = True
        with open(self.report, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
        code = subprocess.call([
            sys.executable, CLI, "validate-live-report", self.report, "--json"
        ], cwd=ROOT)
        self.assertEqual(code, 1)

    def test_completed_report_requires_environment_and_deployment_evidence(self):
        data = self._create()
        for item in data["checks"]:
            item["status"] = "PASS"
        data["final"]["live_revit_validated"] = True
        data["environment"]["revit_build"] = "2026-test"
        data["environment"]["pyrevit_version"] = "6.5.x"
        data["environment"]["pyrevit_engine"] = "IronPython"
        with open(self.report, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
        code = subprocess.call([
            sys.executable, CLI, "validate-live-report", self.report, "--json"
        ], cwd=ROOT)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
