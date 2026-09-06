# Rehabilitation measures v1 — legacy intake registry

`registry.json` is the original broad discovery/intake catalog used to record candidate measures and conservative publication states at the time of the first rehabilitation-library build. It is **not** the source of truth for the current executable measure library after later RMD/ePROVIDE review waves.

Current execution/publication authority is:

- `/content/global-measures-v1/catalog.json` — whether a measure is an actual executable/printable Rawafid tool and its current route.
- `/content/global-measures-v1/rmd-eprovide-rights-audit.json` — current reproduction/rights/Arabic decision.
- The live route under `/sectors/rehabilitation/measures/.../` — the currently published implementation.

When a measure is promoted from the intake catalog after a later rights review, the global catalog/rights ledger supersede the legacy `status` field. The rehabilitation hub runtime reconciles legacy table rows to the current executable routes so users are not shown a stale publication state.

Examples promoted after the v1 intake snapshot include BBS, MAS, MTS, mRS, FAC and BBT. Do not use `registry.json` alone to decide whether one of these tools is currently publishable.
