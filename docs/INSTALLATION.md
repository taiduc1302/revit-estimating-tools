# Installation and Deployment

## Supported deployment shape

The deployable unit is exactly:

```text
RevitEstimating.extension/
  extension.json
  LICENSE
  config/
    categories.json
  lib/
    revit_estimating/
      ...
  Estimating.tab/
    ...
```

The extension is self-contained. It does not require repository-level `lib/`, `config/`, `tests/`, `docs/`, or `tools/` folders at runtime.

pyRevit searches configured extension root directories for folders ending in `.extension`. The directory configured in pyRevit should therefore be the **parent** of `RevitEstimating.extension`, not the `lib` folder and not one of the tab/panel folders.

## Option A — use a repository checkout

1. Clone the repository.
2. Add the repository root to pyRevit's custom extension directories.
3. Reload pyRevit.
4. Confirm that the **Estimating** tab appears.

The repository root contains `RevitEstimating.extension`, so pyRevit can discover it directly.

## Option B — deploy only the extension folder

Copy or symlink the complete `RevitEstimating.extension` folder into any directory already configured as a pyRevit extension root.

Do not copy only `Estimating.tab`. The extension-local `lib/`, `config/`, and `extension.json` are required.

## Option C — build a deterministic deployment ZIP

From the repository root:

```bash
python tools/revit_estimating.py build-extension --output dist/RevitEstimating.extension.zip --json
```

The command:

- runs the offline doctor first;
- packages only `RevitEstimating.extension`;
- excludes Python cache files;
- uses stable file ordering and ZIP timestamps;
- reports the resulting ZIP SHA-256;
- embeds `deployment_manifest.json` containing SHA-256 for every deployed runtime file.

After extraction, verify that the path is:

```text
<configured-extension-root>/RevitEstimating.extension/extension.json
```

and **not**:

```text
<configured-extension-root>/RevitEstimating.extension/RevitEstimating.extension/extension.json
```

## Offline install check

A repository checkout can be checked with:

```bash
python tools/revit_estimating.py doctor --json
```

A copied standalone extension can be checked with:

```bash
python tools/revit_estimating.py doctor <path-to-RevitEstimating.extension> --json
```

A passing standalone doctor confirms the expected `.extension` folder suffix, extension structure, runtime library, governed config, license notice, button metadata, read-only transaction contract, and absence of legacy repository-path injection. When `deployment_manifest.json` is present (as it is in the built ZIP), doctor also verifies that every declared deployed file is present and unchanged and that no undeclared runtime files were added. Passing the outer folder of an accidentally double-nested extraction fails rather than being treated as a repository root. It does **not** prove Autodesk Revit runtime behavior.

The GitHub Actions Python 3.12 job retains the verified `RevitEstimating.extension.zip` as a workflow artifact for 30 days, so the exact CI-tested package can be used for the first live Revit validation instead of rebuilding it locally.

## First live Revit validation

The first real Revit installation must still complete the acceptance checklist in Issue #2 before the extension is treated as production-ready. In particular, verify ribbon loading, IronPython execution, host/link extraction, quantity semantics, transforms, dirty-state behavior, and performance on representative models.

Until that gate is complete, outputs remain `NOT_ESTIMATOR_VALIDATED`.
