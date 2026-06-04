# Audit Evidence

This directory stores lightweight evidence records that should remain in Git.

Generated runtime directories such as `outputs/` and `profiling/output/` are intentionally excluded from active Git tracking after the 2026-05-01 repo hygiene pass. When a run needs to be preserved for future review, record a concise evidence note here instead of committing the full generated run tree.

Recommended evidence note contents:

- source run directory
- run id and status
- model/provider
- validation result
- important artifact checksums
- known issues

