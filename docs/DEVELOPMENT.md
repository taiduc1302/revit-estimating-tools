# Development

## Repository layout

- `RevitEstimating.extension/` — self-contained pyRevit deployment unit.
- `RevitEstimating.extension/lib/revit_estimating/` — reusable business logic and Revit adapter; pyRevit automatically adds an extension-local `lib/` directory to command module paths.
- `RevitEstimating.extension/config/` — governed runtime category configuration.
- `schemas/` — machine-readable schema descriptions.
- `tests/` — tests that run without Autodesk Revit.
- `.github/workflows/` — continuous integration.

## Compatibility approach

The core intentionally avoids third-party dependencies. Revit API imports stay behind adapter modules so core tests can run in standard Python. Ribbon command scripts do not patch `sys.path`; they rely on pyRevit's native extension-local `lib/` module path. Offline tools/tests explicitly add `RevitEstimating.extension/lib` because they run outside pyRevit.

When adding features:

1. keep model reads in the adapter layer;
2. convert Revit objects into plain dictionaries;
3. implement transformation/audit/diff logic against plain dictionaries;
4. add unit tests before expanding the pyRevit UI;
5. never silently invent missing estimating data.

## Versioning

Update `RevitEstimating.extension/lib/revit_estimating/__init__.py`, documentation and extension metadata together for releases. Do not create repository-level copies of the runtime package or category config; the extension folder is the single runtime source of truth.
