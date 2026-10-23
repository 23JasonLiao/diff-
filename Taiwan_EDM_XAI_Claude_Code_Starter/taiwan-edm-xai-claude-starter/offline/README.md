# GPU EDM integration: deliberately not yet implemented

Do not fabricate an EDM adapter without the actual training/inference/network source, data layout, checkpoint and normalization statistics.

Steps when actual files become available:
1. `edm-integrator` agent audits code and writes verified input/output shape contract.
2. Import the original inference functions with minimal modifications, preserving checkpoint and sampler settings.
3. Add a `compute_case(condition, baseline_seeds, perturbation_spec)` adapter that runs BOTH paired conditions with identical random draws.
4. Save `D_theta` estimates at precisely defined sigma/call positions, never raw sampler states mislabeled as rainfall.
5. Add actual U-Net hooks for canonical stages; vectorize on GPU or stream safely, avoiding graph retention.
6. Write versioned cache with `data_status=actual_edm`, checkpoint SHA256 and experiment provenance, and run real acceptance tests.
7. Use `specs/ARCHITECTURE.md` budget to constrain Cartesian perturbation combinations.

Pilot: 12 case dates x 2 variables x 2 amplitudes x 3 input regions = 144 perturbed experiments plus 12 shared baselines. Confirm physical plausibility and IO size before scaling to full test period.
