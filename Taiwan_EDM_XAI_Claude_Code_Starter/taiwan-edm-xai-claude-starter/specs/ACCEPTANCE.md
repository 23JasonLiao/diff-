# Acceptance tests and gates

P0 Scientific unit tests
- identical baseline/perturbed => delta_mean=0, delta_sd=0, W1=0, delta_tail=0, variance decomposition=0.
- constant +c addition per member => delta_mean=c, delta_sd=0, W1=abs(c), var delta=0.
- affine scale >1 increases standard deviation and sample variance as expected.
- `var(P)-var(B)` equals `var(delta)+2cov(B,delta)` up to numerical tolerance.
- one member spatial mean before spread; verify different spatial patterns do not create fake ensemble spread.
- cohort median of case effects does not equal pooled member effect by accident.

P1 Data API tests
- synthetic data identified with `data_status=synthetic_demo` in all responses.
- invalid Output ROI and unavailable cache key return explicit 4xx errors.
- API documented in Swagger under `/docs`.
- API must not import `torch`, `cuda`, network module or access GPU.
- inputs/outputs include units, counts, step sigma metadata and provenance.

P2 Full integration tests with actual checkpoint (future)
- input shape and channel order verified against current training/inference scripts.
- same seed baseline run is bitwise/tolerance reproducible on same hardware/config.
- no-op perturbation produces identical samples and all-zero effects.
- reconstructed rainfall equals legacy inference within tolerance in physical units.
- ROI mean on CPU from cache equals direct post-inference ROI mean.
- same-date paired runs share every stochastic draw required by sampler.
- correct handling of 40 denoising levels and optional Heun predictor/corrector calls.
- cohort composition computed using documented pre-perturbation filters.
