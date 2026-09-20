# API Compatibility Notes

This document records compatibility assumptions that should be re-checked when changing Revit or pyRevit targets.

## Current pilot target

- pyRevit: 6.5.x (pilot reference: 6.5.5)
- Revit API declared minimum: Revit 2021+. Compatibility-critical BuiltInParameter identifiers were cross-checked against the Revit 2021.1 enumeration as well as the 2026 reference; actual Revit 2021 runtime behavior remains a live-validation item.
- V0.1 UI scripts: default pyRevit IronPython engine

## Why the UI scripts stay on the default Python engine

The commands use `pyrevit.forms.pick_file` and `pyrevit.forms.pick_folder`. Current pyRevit source implements these helpers in the IronPython forms layer, while the CPython forms compatibility layer marks them unsupported. Do not add a `#! python3` shebang to the four V0.1 button scripts until their UI/file-picker path is replaced or CPython support changes.

The extension contract tests intentionally reject a Python 3 shebang on these commands. CI also runs a static IronPython-compatibility proxy across runtime Python sources to reject obvious Python-3-only syntax and selected standard-library/runtime APIs. This is a regression guard, not a substitute for executing the extension under pyRevit IronPython.

## Revit 2021.1 / 2026 BuiltInParameter checks

The adapter parameter set is maintained against current Revit references. Compatibility-critical MEP identifiers including `RBS_PIPE_MATERIAL_PARAM`, `RBS_CTC_SERVICE_TYPE`, `RBS_CABLETRAYCONDUIT_SYSTEM_TYPE`, `RBS_CABLETRAYCONDUITRUN_LENGTH_PARAM`, and `RBS_DUCT_SIZE_FORMATTED_PARAM` were also confirmed in the Revit 2021.1 BuiltInParameter enumeration.

The following parameters are used by the adapter:

### Project metadata

- `PROJECT_NAME`
- `PROJECT_NUMBER`

### Identity/context and level fallbacks

- `LEVEL_PARAM`
- `FAMILY_LEVEL_PARAM`
- `INSTANCE_REFERENCE_LEVEL_PARAM`
- `INSTANCE_SCHEDULE_ONLY_LEVEL_PARAM`
- `SCHEDULE_LEVEL_PARAM`
- `SCHEDULE_BASE_LEVEL_PARAM`
- `RBS_START_LEVEL_PARAM`

### Generic quantity parameters

- `CURVE_ELEM_LENGTH`
- `INSTANCE_LENGTH_PARAM`
- `HOST_AREA_COMPUTED`
- `HOST_VOLUME_COMPUTED`

### Pipe / duct / conduit / cable tray

- `RBS_PIPE_DIAMETER_PARAM`
- `RBS_CONDUIT_DIAMETER_PARAM`
- `RBS_CURVE_DIAMETER_PARAM`
- `RBS_CURVE_WIDTH_PARAM`
- `RBS_CURVE_HEIGHT_PARAM`
- `RBS_CABLETRAY_WIDTH_PARAM`
- `RBS_CABLETRAY_HEIGHT_PARAM`
- `RBS_CALCULATED_SIZE`
- `RBS_DUCT_SIZE_FORMATTED_PARAM`
- `RBS_SYSTEM_NAME_PARAM`
- `RBS_PIPING_SYSTEM_TYPE_PARAM`
- `RBS_DUCT_SYSTEM_TYPE_PARAM`
- `RBS_CABLETRAYCONDUIT_SYSTEM_TYPE`
- `RBS_SYSTEM_CLASSIFICATION_PARAM`
- `RBS_CTC_SERVICE_TYPE`
- `RBS_CABLETRAYCONDUITRUN_LENGTH_PARAM`
- `RBS_PIPE_VOLUME_PARAM`
- `RBS_PIPE_MATERIAL_PARAM`

### Material and common estimating metadata

- `STRUCTURAL_MATERIAL_PARAM`
- `MATERIAL_ID_PARAM`
- `ALL_MODEL_MARK`
- `ALL_MODEL_DESCRIPTION`
- `ALL_MODEL_INSTANCE_COMMENTS`
- `ALL_MODEL_TYPE_COMMENTS`
- `ALL_MODEL_MODEL`
- `UNIFORMAT_CODE`
- `KEYNOTE_PARAM`

## Important limitations

Presence in the API enumeration does not guarantee that a parameter exists or has a value on every element/category. The adapter therefore treats these as ordered fallbacks and then tries selected display-name lookups. Missing values remain missing and are handled by model-audit rules; they must not be invented.

Display-name fallbacks are currently English (`Material`, `Level`, `Reference Level`, `System Type`, and similar). Built-in parameters are preferred, but non-English Revit/model environments remain a live-validation requirement.

The adapter exposes one primary `material` value for grouping. It does not yet expand compound wall/floor layers or all multi-material family cases.

## References used for the compatibility review

- Autodesk Revit API / RevitAPIDocs 2021.1 and 2026 BuiltInParameter enumerations
- pyRevit extension metadata and IronPython/CPython forms implementations

Re-check these assumptions when upgrading pyRevit or changing the supported Revit range.
