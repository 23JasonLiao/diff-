# Taiwan Atmospheric EDM XAI: coding contract

## Mission
Build a CPU-only interactive Visual Analytics/XAI system over **GPU-precomputed** paired Taiwan EDM samples. Research priority: input atmospheric/physical hypothesis -> final rainfall ensemble distribution (especially spread) -> paired member responses and cohort repeatability. EDM step/layer summaries are secondary evidence.

## Read before code changes
1. `specs/PRD.md` (scientific scope and non-goals)
2. `specs/CACHE_CONTRACT.md` (tensor axes, identities, provenance)
3. `specs/ARCHITECTURE.md` (offline/online boundary)
4. `specs/PHYSICAL_MAPPING.md` (physical mapping and cohort semantics)
5. `specs/ACCEPTANCE.md` (test gates)
6. `docs/PLAN.md` (incremental milestones)

## Invariants (MUST)
- **Never run U-Net, torch CUDA, or EDM inference inside `backend/` or `frontend/`.** All model passes are performed in offline GPU jobs.
- Baseline/perturbation for each case must reuse the SAME seed identities, same noise schedule and all sampler randomness. Never compare mismatched seeds as paired samples.
- An ensemble member is ONE spatial rainfall field. For Output ROI, reduce each member spatially first, then compute a 30-sample distribution. Never flatten pixel x member and label its variance ensemble spread.
- Cohort statistics aggregate independent case-level effects. Never flatten case x member as the primary cohort metric.
- Preserve sample IDs, time, variable, region mask identifier, amplitude in training-standard-deviation units, checkpoint/config hashes, sampler settings, units, ROI definition, and synthetic-vs-actual data status.
- `q700`, `u/v`, `t2m`, `msl`, `tp` map to physical hypotheses, NOT proven atmospheric causation. Joint perturbations require plausibility checks. Perturbing `tp` must distinguish network-condition-only and reconstruction-baseline effects.
- Cache miss must be a clear error. Never interpolate uncomputed model results and never label synthetic demonstration data as measured EDM output.
- Canonical input example uses `[B,7,112,72]` conditional inputs, residual `[B,1,112,72]`, 30 members, 40 denoising levels. Verify actual files before locking any deeper layer/channel shapes.
- During refactors protect existing tests, small scope PRs, spec updates before API/schema changes; no broad rewrites or silent math modifications.

## Workflow
1. Identify the spec section and acceptance test.
2. Write a short execution plan; for broad requests use Plan mode.
3. Implement one vertical slice (contract -> tests -> backend -> frontend).
4. Delegate **read-only** code/math reviews to `scientific-reviewer` or `qa-reviewer` where appropriate.
5. Run `python -m pytest backend/tests -q`, and frontend build when dependencies are available.
6. Update docs/PLAN.md and summarize changed files, tests, known limitations.

## Architecture ownership
- `offline/`: EDM import/checkpoint adapter and GPU precompute ONLY; cannot run here without actual model/dataset.
- `backend/app/`: CPU-only NumPy/statistics, cache lookup and FastAPI endpoints.
- `frontend/`: React interface, case/cohort drilldown, maps and charts.
- `data/demo/`: **SYNTHETIC ONLY**, generated with `scripts/generate_demo_cache.py`.
- `specs/`: source of truth; `docs/PLAN.md` records decisions and status.

## Quality
- Prefer explicit dimensions and units in docstrings and API responses.
- Use pytest for metric identities and shape validation.
- Do not silently clip or renormalize rainfall without a documented scientific rule.
- Ensure CPU-only behavior with runtime tests (not just a comment).
- Ask for permission before destructive commands or changing study definitions.
