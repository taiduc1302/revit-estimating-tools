from __future__ import absolute_import

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "tools", "revit_estimating.py")
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")


class LiveValidationReportTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.report = os.path.join(self.root, "live.json")

    def tearDown(self):
        shutil.rmtree(self.root)

    def _build_deployment(self):
        deployment = os.path.join(self.root, "RevitEstimating.extension.zip")
        raw = subprocess.check_output([
            sys.executable, CLI, "build-extension",
            "--output", deployment, "--json",
        ], cwd=ROOT)
        payload = json.loads(raw.decode("utf-8"))
        self.assertTrue(payload.get("passed"), payload)
        return deployment, payload

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

    def test_live_validation_kit_is_deterministic_and_complete(self):
        deployment, deployment_payload = self._build_deployment()
        first = os.path.join(self.root, "first-kit.zip")
        second = os.path.join(self.root, "second-kit.zip")
        for output in (first, second):
            raw = subprocess.check_output([
                sys.executable, CLI, "build-live-kit",
                "--deployment-zip", deployment,
                "--output", output,
                "--commit", "abc123",
                "--workflow-run", "999",
                "--artifact-id", "12345",
                "--json",
            ], cwd=ROOT)
            payload = json.loads(raw.decode("utf-8"))
            self.assertTrue(payload.get("passed"), payload)
            self.assertEqual(payload["deployment_zip_sha256"], deployment_payload["sha256"])

        def digest(path):
            hasher = hashlib.sha256()
            with open(path, "rb") as stream:
                hasher.update(stream.read())
            return hasher.hexdigest()

        self.assertEqual(digest(first), digest(second))
        with zipfile.ZipFile(first, "r") as archive:
            names = set(archive.namelist())
            self.assertEqual(names, set([
                "README_LIVE_VALIDATION.md",
                "RevitEstimating.extension.zip",
                "SHA256SUMS.txt",
                "docs/RELEASE_CHECKLIST.md",
                "docs/TESTING.md",
                "live_validation_report.json",
            ]))
            report = json.loads(archive.read("live_validation_report.json").decode("utf-8"))
            checksums = archive.read("SHA256SUMS.txt").decode("utf-8")
            nested_zip = archive.read("RevitEstimating.extension.zip")

        self.assertEqual(report["deployment"]["source_commit"], "abc123")
        self.assertEqual(report["deployment"]["workflow_run"], "999")
        self.assertEqual(report["deployment"]["artifact_id"], "12345")
        self.assertEqual(report["deployment"]["extension_path"], "")
        self.assertEqual(
            report["deployment"]["deployment_zip_sha256"],
            hashlib.sha256(nested_zip).hexdigest(),
        )
        self.assertIn(report["deployment"]["deployment_zip_sha256"] + "  RevitEstimating.extension.zip", checksums)
        self.assertFalse(report["final"]["live_revit_validated"])
        self.assertFalse(report["final"]["production_ready"])

    def test_live_validation_kit_report_matches_nested_deployment_files(self):
        deployment, _ = self._build_deployment()
        kit = os.path.join(self.root, "kit.zip")
        subprocess.check_output([
            sys.executable, CLI, "build-live-kit",
            "--deployment-zip", deployment,
            "--output", kit,
            "--commit", "abc123",
            "--workflow-run", "999",
            "--json",
        ], cwd=ROOT)

        with zipfile.ZipFile(kit, "r") as outer:
            report = json.loads(outer.read("live_validation_report.json").decode("utf-8"))
            nested_bytes = outer.read("RevitEstimating.extension.zip")
        nested_path = os.path.join(self.root, "nested.zip")
        with open(nested_path, "wb") as stream:
            stream.write(nested_bytes)

        with zipfile.ZipFile(nested_path, "r") as nested:
            expected = {
                "extension_manifest_sha256": nested.read("RevitEstimating.extension/extension.json"),
                "deployment_manifest_sha256": nested.read("RevitEstimating.extension/deployment_manifest.json"),
                "categories_config_sha256": nested.read("RevitEstimating.extension/config/categories.json"),
            }
        for field, raw in expected.items():
            self.assertEqual(report["deployment"][field], hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
