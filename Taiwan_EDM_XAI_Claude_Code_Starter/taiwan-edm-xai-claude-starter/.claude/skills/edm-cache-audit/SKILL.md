---
name: edm-cache-audit
description: Audit the real Taiwan EDM checkpoint, inference and GPU cache fidelity including seeds, denoiser, units, sigma levels and feature vectors. Use when adapting existing EDM code or validating a precompute run.
---
1. Require actual inference, training, network and data preprocessing source. If not provided, list missing inputs, do not guess.
2. Trace case -> C -> residual target -> noisy state -> EDMPrecond D -> solver -> mm/day reconstruction.
3. Enumerate all random draws and ensure baseline/perturbed share identical draws for each member.
4. Specify step semantics, sigma values, predictor/corrector calls, hook outputs, shape/dtype and storage budget.
5. Confirm `tp` perturbation's condition-only/baseline-only/end-to-end mode.
6. Test a no-op perturbation and compare cached vs original inference outputs in physical units.
7. Report data lineage and checksums; do not claim success from synthetic tests.
