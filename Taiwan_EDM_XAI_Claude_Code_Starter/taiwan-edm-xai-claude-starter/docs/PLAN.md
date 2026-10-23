# Delivery plan and status

- [x] Phase 0: Define domain contract, architecture, acceptance, Claude Code agent controls.
- [x] Phase 1 demo: CPU metrics and toy data generation with tests.
- [x] Phase 2 demo: Minimal FastAPI + React shell reading synthetic cache.
- [ ] Phase 3: Import **actual user-provided** trained EDM model/inference/data pipeline; run strict numerical golden test on one case.
- [ ] Phase 4: GPU offline paired full-coverage cache for a deliberately small pilot grid.
- [ ] Phase 5: Add exact step sigma/calibration and selected real feature hooks.
- [ ] Phase 6: Production maps/cohort/physical-condition concept builder and usability evaluation.

`[x] demo` does NOT imply genuine Taiwan EDM inference or research validation.

## Implementation order for Claude
1. Audit model code + make actual cache contract; do not start modifying network.
2. Implement one real baseline and a no-op perturbed run, then matched +0.5sigma q700 north.
3. Test output physical units, seeds, dimensions, reconstruction and 40 levels.
4. Backfill cache and compare CPU API result to small NumPy reference.
5. Only then expand variables, input ROIs and cohorts; keep a coverage budget.
