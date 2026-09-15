# Testing

## Automated tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the dependency-free suite on supported Python versions.

## Live Revit validation checklist

Automated tests do not replace a Revit test. Before calling a release production-ready, validate on representative models:

1. tab and all four buttons load in pyRevit;
2. Model Audit completes without starting a Revit transaction;
3. host and loaded links are discovered correctly;
4. supported categories extract expected family/type/system/material/level data;
5. Revit internal units normalize correctly against known measurements;
6. link-instance transforms produce sensible host-coordinate locations;
7. unloaded links are flagged;
8. snapshot files open and hashes validate;
9. two controlled revisions produce expected added/removed/modified results;
10. no model dirty-state change is caused by the extension.

Record Revit build, pyRevit version, model type and observed discrepancies for every live validation.
