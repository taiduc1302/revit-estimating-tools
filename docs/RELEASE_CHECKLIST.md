# Release Checklist

V0.1 must not be tagged or described as production-ready until live Autodesk Revit validation is complete.

## Offline gate

Before any release candidate handoff:

- [ ] PR CI is green on Python 3.8, 3.11, and 3.12.
- [ ] Offline doctor passes.
- [ ] Unit tests pass.
- [ ] Golden revision comparison passes.
- [ ] Self-contained extension ZIP builds deterministically.
- [ ] Extracted deployment ZIP passes standalone doctor.
- [ ] Deployment manifest hashes validate.
- [ ] Synthetic comparison benchmark passes the CI threshold.
- [ ] PR remains mergeable.
- [ ] No company-specific or live tender/project names exist in deployable source/docs.
- [ ] All outputs remain `NOT_ESTIMATOR_VALIDATED`.

## Live Revit gate

Complete Issue #2 on representative Autodesk Revit models:

- [ ] pyRevit loads the extension and all four ribbon commands.
- [ ] Model Audit and Extract Snapshot execute on the intended IronPython engine.
- [ ] No command dirties or modifies the Revit model.
- [ ] Host and linked-model discovery is correct.
- [ ] Linked transforms produce correct host coordinates.
- [ ] Unloaded links and extraction failures are visible as audit findings.
- [ ] Category-level quantities reconcile against known Revit schedules and/or drawing quantities.
- [ ] Wall/floor area semantics are documented and approved.
- [ ] Structural framing length semantics are documented and approved.
- [ ] Foundation volume semantics are documented and approved.
- [ ] MEP system/material/size fallbacks are confirmed on representative models.
- [ ] Save As preserves host identity.
- [ ] Repeated and reinserted links behave as designed.
- [ ] Non-English/localized model fallbacks are tested if relevant.
- [ ] Large-model extraction time and memory are recorded.
- [ ] Snapshot and comparison packages validate after real extraction.

## Release decision

Only after the live gate passes:

1. Update `docs/FINAL_AUDIT.md`:
   - `LIVE_REVIT_VALIDATED: true`
   - set `PRODUCTION_READY` only if quantity semantics and runtime behavior are accepted.
2. Change `CHANGELOG.md` from `0.1.0 - Unreleased` to a dated release entry.
3. Confirm `RevitEstimating.extension/lib/revit_estimating/__init__.py` version.
4. Rebuild the deterministic deployment ZIP.
5. Record:
   - git commit SHA;
   - CI run number;
   - deployment ZIP SHA-256;
   - Revit build;
   - pyRevit version;
   - tested model types.
6. Create the release/tag only after those records are attached to the release notes.

## Current state

- OFFLINE_VALIDATED: true
- LIVE_REVIT_VALIDATED: false
- PRODUCTION_READY: false
- Release tag permitted: no
