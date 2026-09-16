# Development

## Repository layout

- `RevitEstimating.extension/` — pyRevit user interface and thin command scripts.
- `lib/revit_estimating/` — reusable business logic and Revit adapter.
- `config/` — supported category configuration.
- `schemas/` — machine-readable schema descriptions.
- `tests/` — tests that run without Autodesk Revit.
- `.github/workflows/` — continuous integration.

## Compatibility approach

The core intentionally avoids third-party dependencies. Revit API imports stay behind adapter modules so core tests can run in standard Python. Command scripts prepend the repository `lib` folder to `sys.path`.

When adding features:

1. keep model reads in the adapter layer;
2. convert Revit objects into plain dictionaries;
3. implement transformation/audit/diff logic against plain dictionaries;
4. add unit tests before expanding the pyRevit UI;
5. never silently invent missing estimating data.

## Versioning

Update `lib/revit_estimating/__init__.py`, documentation and extension metadata together for releases.
