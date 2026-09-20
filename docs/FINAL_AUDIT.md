# Final Offline Audit — V0.1

Initial audit date: 2026-09-16
Follow-up hardening audit: 2026-09-19

## Status

- `OFFLINE_VALIDATED`: true — post-audit CI passed on Python 3.8, 3.11, and 3.12
- `LIVE_REVIT_VALIDATED`: false
- `PRODUCTION_READY`: false until live Revit/pyRevit validation in Issue #2 is completed
- Model modification: not implemented
- Pricing/write-back: not implemented

This audit is a reviewer-style inspection of the repository, not a substitute for executing the extension inside Autodesk Revit.

## Audit scope

The audit reviewed:

- pyRevit extension/bundle structure and command contexts;
- read-only safety assumptions;
- Revit API parameter and collector usage;
- host/link identity and revision matching;
- quantity aggregation and audit-only behavior;
- snapshot/comparison evidence integrity;
- error handling and partial-extraction visibility;
- regression tests and CI coverage;
- neutral naming and absence of company-specific branding;
- estimator-facing failure modes such as wrong-project comparison and false quantity changes.

## Findings fixed during final audit

### Audit-only categories were still aggregating quantities

`Generic Models` is configured as `audit_only`, but that flag was not propagated into the DTO or aggregation layer. Audit-only elements now carry `quantity_aggregation_excluded: true` and are excluded from quantity summaries and revision quantity deltas while remaining available for model-audit review.

### Category collection failures could look like legitimate zero quantities

The Revit category collector previously returned an empty list for both a genuinely empty category and a Revit API/configuration exception. Collection failures now produce a HIGH `CATEGORY_COLLECTION_FAILED` audit issue and are recorded in `skipped_categories` metadata. Link-collection and unresolved-link-transform failures are also surfaced instead of being silent.

### Revision comparison missed movement and estimating metadata changes

Exact-identity elements could move or change classification metadata without becoming `MODIFIED`. Revision comparison now tracks representative host-coordinate location and selected estimating metadata including description, comments, type comments, Assembly Code, keynote, and model.

### Optional run log was packaged without integrity coverage

`run_log.json` could be included in the ZIP without a manifest hash. The run log is now registered in `evidence_hashes`; validation detects missing, unregistered, or tampered run-log evidence before packaging.

### CSV export omitted selected estimating parameters

`elements.csv` now includes the `parameters` object and `quantity_aggregation_excluded` flag so CSV review does not silently omit fields that exist in `raw_snapshot.json`.

### Pipe material extraction needed a stronger built-in fallback

The adapter now tries `RBS_PIPE_MATERIAL_PARAM` before generic material fallbacks.

### Wrong-project comparison needed an explicit guard

When both snapshots contain Revit Project Number values and they differ, comparison emits a HIGH `PROJECT_NUMBER_MISMATCH` warning. It remains a warning rather than an automatic rejection because project-number conventions vary and can legitimately be corrected between revisions.

### Ribbon commands needed user-facing failure handling

Model Audit, Extract Snapshot, and Compare Revision now catch top-level failures and show a controlled pyRevit alert rather than exposing a raw traceback as the normal user experience.

### Category configuration was fail-open and repeatedly read during audit

The runtime category loader previously fell back silently to a built-in list when the governed `config/categories.json` was missing or invalid. That could produce plausible quantities from a config different from the one named in the manifest. In addition, `audit_element()` reached `load_category_specs()` through `spec_by_name()` for every element, creating avoidable file I/O on large models.

The loader is now fail-closed, validates schema/duplicates/quantity types/control flags, caches the validated specs for the command, and records config SHA-256/schema/category-count provenance in every extracted snapshot.

### IronPython compatibility needed a stronger offline regression guard

Python 3.8/3.11/3.12 CI does not prove IronPython 2.7 syntax/runtime compatibility. A static runtime-source contract now rejects obvious Python-3-only constructs, annotations/keyword-only arguments, selected Python-3-only stdlib APIs, and builtin `open(..., encoding=...)` usage. Live pyRevit execution remains required.

### Revision comparison trusted orphaned raw snapshots

Compare Revision previously validated snapshot schema/identity but did not require the selected raw JSON to still belong to an intact exported snapshot package. A modified or orphaned `raw_snapshot.json` could therefore be hashed as a new comparison input without first proving it still matched its snapshot manifest. pyRevit and the CLI now require intact validated snapshot packages by default. Standalone raw JSON is available only through the explicit CLI `--allow-standalone` development/fixture override and is labelled `STANDALONE_UNVERIFIED` in comparison evidence.

### Spreadsheet CSV output allowed formula-like text

CSV evidence is commonly opened in Excel. Text values beginning with spreadsheet formula prefixes could therefore be interpreted as formulas even though the underlying BIM value was only text. CSV serialization now prefixes formula-like text with an apostrophe while leaving true numeric values unchanged. Raw JSON evidence preserves the original value.

### Manifest status and metadata could diverge from hashed raw evidence

The manifest is the hash index for package evidence and is not itself inside its own hash set. Validation now requires `NOT_ESTIMATOR_VALIDATED`, checks the expected tool identity, and verifies that mirrored manifest metadata matches the metadata embedded in hashed `raw_snapshot.json`. Comparison manifests apply the same status/tool contract. This catches accidental or naive status escalation, but it does not provide cryptographic authenticity against an actor who can rewrite the manifest and recompute all hashes.

### Comparison input metadata was under-validated when source files were intentionally skipped

`validate-comparison --skip-input-files` is intended to waive only the requirement that original snapshots still exist at their recorded paths. It now continues to validate recorded input path/hash/status/package-status structure, including SHA-256 format.

### Recreated-element inference used greedy first-match selection

A removed element processed earlier could claim a current element even when another removed element was a materially better match. `POSSIBLE_RECREATED` now requires reciprocal, unambiguous best matches in both directions. Inferred identity remains advisory.

### Audit issue identities could collide for repeated link problems

Model-level/link issues with the same rule and message could share an `issue_id` even when their trace values referred to different link instances. Issue identity now includes source and deterministic values such as `link_instance_id`.

### Non-finite JSON and non-positive quantities needed stricter fail-closed behavior

Canonical JSON serialization now rejects `NaN` and `Infinity` rather than emitting non-standard JSON. Primary quantities less than or equal to zero remain visible in element evidence and trigger HIGH audit findings, but they are excluded from aggregated totals and revision quantity deltas so an invalid negative value cannot reduce a takeoff total.

### Per-element extraction failure severity was too low

If one element cannot be extracted, the resulting snapshot can be quantity-incomplete. `ELEMENT_EXTRACTION_FAILED` is now HIGH severity rather than MEDIUM.

### CLI package output could overwrite source evidence

The offline `package --output` path previously accepted any filename, including `manifest.json` or another evidence file inside the source snapshot folder. Packaging now rejects output paths that collide with required or optional snapshot evidence before opening the ZIP for writing.

### Large recreated-element candidate sets could become quadratic

Recreated-element inference is advisory and is now bounded per logical scope/category bucket. If a bucket exceeds 250,000 candidate pairs, inference is skipped for that bucket, the elements remain explicit `ADDED`/`REMOVED` records, and the comparison emits `RECREATED_MATCH_SKIPPED_LARGE_BUCKET`. A synthetic offline benchmark is included to detect future performance regressions.

### Reinserted Revit links could look like wholesale scope change without context

Linked-element identity intentionally includes the link-instance scope. If a link is removed and reinserted, its instance identity may change and many elements can legitimately appear `ADDED`/`REMOVED`. Comparison now emits `LINK_SCOPE_SET_CHANGED` when linked scopes differ and `LINK_INSTANCE_IDENTITY_CHANGED` when the same linked document/name evidence appears with different scope identities.

### Derived CSV evidence could drift while hashes were recomputed

SHA-256 checks alone could not distinguish a legitimate regenerated CSV from a modified CSV whose manifest hash had also been updated. Snapshot validation now deterministically regenerates all four CSV review surfaces from authoritative `raw_snapshot.json` and requires byte-equivalent text. Revision-comparison validation does the same for its two CSV outputs from `revision_diff.json`. When recorded baseline/current snapshots remain available, the validator also recomputes the entire revision result and compares it to `revision_diff.json`.

### Wrong-project protection needed a fallback when Project Number is blank

A blank Revit Project Number is common enough that number-only mismatch detection was insufficient. Comparison now falls back to populated Revit Project Name values: differing names are HIGH when a shared populated project number is unavailable, and MEDIUM when both snapshots share the same project number.

### Linked coordinates could be mislabeled when transform resolution failed

If a linked model transform was missing, or a resolved transform failed during `OfPoint()`, retaining the original point would make link-local coordinates look like host coordinates. Linked elements now publish `location: null` unless the host transform is available and applies successfully. Link scope fallback also prefers Revit link instance ElementId before link name when UniqueId is unavailable, reducing collisions between same-named instances.

### JSON parsing needed to be strict as well as JSON writing

The serializer already stopped emitting non-finite numbers, but Python's default JSON parser can accept `NaN`/`Infinity`. `read_json()` now rejects those constants so imported snapshot/comparison evidence follows the same strict numeric contract in both directions. Validator recomputation failures are reported as findings instead of escaping as raw exceptions when evidence structure is malformed.

### Category configuration provenance stored only a digest

The snapshot recorded the SHA-256 and metadata of the extension-local `config/categories.json`, but not the exact rules file itself. A historical package could therefore prove that a particular digest was declared without preserving the configuration needed to reproduce or inspect the extraction rules. Snapshots now embed `categories_config.json`; validation cross-checks its evidence hash, provenance SHA-256, schema version, and category count.

### Runtime deployment depended on repository-neighbor folders

The original button scripts manually prepended a repository-level `lib/` path, while governed config also lived outside the `.extension` folder. Copying only `RevitEstimating.extension` could therefore leave a ribbon that loaded but failed at runtime. V0.1 now uses pyRevit's native extension-local `lib/` discovery, carries `config/categories.json` inside the extension, and has no repository-level runtime/config duplicate. Standalone doctor tests copy only the extension folder and verify runtime/config loading without repository neighbors.

### Deployment artifact was not reproducibly buildable

The offline CLI now provides `build-extension`, which first runs doctor and then creates a deterministic ZIP containing only `RevitEstimating.extension`. File ordering and ZIP timestamps are fixed; installability tests build twice and require identical SHA-256 values. CI also builds the artifact on every matrix job.

### Malformed deployment paths could pass a loose structural check

A path ending in `.extension` is now always validated as the deployable extension at that exact location. Doctor rejects missing `.extension` suffixes and fails an outer double-nested `.extension` folder instead of silently treating it as a repository root.

### Deployment ZIP omitted the repository license notice

Because `build-extension` intentionally packages only `RevitEstimating.extension`, a root-only license would be absent from the distributed ZIP. The deployable extension now includes `LICENSE`; doctor requires it, tests require it to match the repository license byte-for-byte, and ZIP tests require it to be present.

### Extracted deployment integrity needed a portable trust record

A deterministic ZIP SHA-256 verifies the archive before extraction, but does not help detect later drift inside an extracted extension folder. Built deployment ZIPs now include `deployment_manifest.json`, which records SHA-256 for every deployed runtime file. Standalone doctor verifies all declared files, rejects hash mismatches and missing files, and reports undeclared added files. CI also extracts the built ZIP and smoke-imports the runtime/config without repository neighbors.

### Verified deployment artifact was not retained for handoff

CI now uploads the Python 3.12 deterministic deployment ZIP as a 30-day GitHub Actions artifact. This allows the first live Revit test to use the exact package that passed the offline installability suite rather than a separately rebuilt copy.

## Controls verified by automated tests

The automated suite covers or statically checks:

- deterministic normalization and serialization;
- stable host identity across file rename / Save As;
- separation of repeated Revit link instances;
- conservative reciprocal-best recreated-element inference;
- duplicate identity and unsupported-schema rejection;
- numeric-size comparison independent of display-unit formatting;
- audit-only exclusion from quantity aggregation;
- movement and Assembly Code revision detection;
- snapshot hash tampering, manifest/raw metadata consistency, and validation-status enforcement;
- run-log hash tampering;
- revision-comparison input/output hashes, source-package integrity enforcement, and structural input-evidence validation even when source-file existence checks are skipped;
- collision-safe output folders;
- project-number mismatch warnings;
- expected pyRevit button structure, clean-engine metadata, project-document context, default IronPython assumption, read-only transaction contract, no repository-path injection, and a static IronPython compatibility proxy;
- standalone `.extension` doctor validation, malformed/double-nested path rejection, copied-runtime/config import, deployable-license parity, and deterministic deployment-ZIP SHA-256;
- fail-closed category configuration loading, caching, and SHA-256 provenance;
- spreadsheet-formula escaping for CSV review surfaces while preserving numeric values;
- rejection of non-finite JSON values and exclusion of non-positive quantities from aggregate totals;
- collision-resistant audit issue identities and HIGH severity for per-element extraction failures;
- absence of the removed company-specific project name in governed source/docs/config/tool paths.

The post-audit GitHub Actions matrix passed the offline doctor, dependency-free unit tests, golden CLI revision comparison, and bytecode compilation on Python 3.8, 3.11, and 3.12.

## Known limitations that remain after offline audit

### Live Autodesk behavior is unverified

No offline test can prove actual Revit category enumeration, parameter availability on representative project families, linked-coordinate transforms, pyRevit ribbon loading, or that Revit's dirty state remains unchanged. These are the live gate in Issue #2.

### Quantity semantics still require estimator validation against schedules/drawings

A technically available Revit parameter is not automatically the correct estimating quantity. Examples include wall/floor computed area conventions, openings, structural-framing nominal versus cut length, foundation volume behavior, and project-specific modeling practices. During live validation, extracted quantities must be reconciled against known Revit schedules and/or drawing quantities before any category is treated as production-approved.

### Source paths are evidence and may contain internal filesystem information

`source_document_identity` can contain the full local/model path and `run_log.json` can contain the chosen export path. Snapshot packages should therefore be treated as internal evidence unless paths are reviewed/redacted before external sharing. Automatic path-redaction is not implemented in V0.1.

### Localization fallbacks are not fully language-independent

Built-in Revit parameters are preferred, but several final fallback lookups use English display names such as `Material`, `Level`, and `System Type`. Phase heuristics for identifying an existing phase also use English text. Non-English Revit/model conventions require live validation.

### Material semantics vary by Revit category

A single `material` field is useful for estimating grouping but does not represent all compound-layer, painted-material, hosted-family, or multi-material cases. Walls/floors and complex families may need a material-breakdown feature in a later version.

### Representative location is not geometry equivalence

Location is a midpoint/point/bounding-box representative coordinate. It is useful for revision review and inferred matching, but it does not prove two element geometries are equivalent.

### Large-model performance is not benchmarked yet

The core algorithms are deterministic and dependency-light, but extraction and serialization have not been profiled on very large production models. Performance acceptance should be recorded during live validation.

### Open-model source file hashing is intentionally not claimed

The snapshot records `source_model_hash_status: NOT_COMPUTED_FOR_OPEN_MODEL`; V0.1 does not claim a SHA-256 hash of the active RVT file because the open document state and disk file may differ.

## Release gate

V0.1 is **offline-ready**. It must remain `NOT_ESTIMATOR_VALIDATED` / not production-ready until Issue #2 is completed on representative Autodesk Revit models and category-level quantity semantics are reconciled against known schedules/drawings.
