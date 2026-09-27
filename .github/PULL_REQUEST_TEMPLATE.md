## Summary

Describe the change and why it is needed.

## Safety contract

- [ ] No Revit write transaction or model write-back was introduced.
- [ ] No network access, telemetry, external process execution, or dynamic eval/exec was introduced.
- [ ] pyRevit button scripts remain compatible with the intended IronPython engine.
- [ ] Core runtime remains dependency-free unless the change explicitly updates the architecture/release gate.
- [ ] Invalid or ambiguous estimating evidence still fails closed.
- [ ] No company-specific or live tender/project names were added.

## Validation

- [ ] Offline doctor passes.
- [ ] Unit tests pass.
- [ ] Golden revision comparison passes.
- [ ] Self-contained extension build passes.
- [ ] Synthetic benchmark passes.
- [ ] Compile check passes.
- [ ] New/changed behavior has regression coverage.

## Revit-dependent change

- [ ] This change does not depend on Autodesk Revit runtime behavior.

If unchecked, describe the required live Revit validation and attach/update the live-validation report / Issue #2 evidence before release approval.

## Release state

- [ ] This PR does not claim `LIVE_REVIT_VALIDATED=true` or `PRODUCTION_READY=true` without completed live evidence.
