# Cache contract v0.1 (subject to real EDM integration review)

## For actual 8-km Taiwan EDM
- condition tensor `[B,7,112,72]`, target / denoised normalized residual `[B,1,112,72]` (verify code).
- output final rainfall `[M,112,72]`, physical unit mm/day, M=30.
- step denoised rainfall `[K,M,112,72]`, K=40 **saved denoiser calls/levels as documented**, not necessarily all Heun calls.
- selected features `[L,K,M,D]`, e.g. L=3 canonical stages and D=32. Shape uniform only AFTER compression.
- High-res land mask `[112,72]` and Output ROI masks same raster axes/order.
- Physical sampling metadata: checkpoint checksum, model code revision, dataset revision, train sigma statistics, seed IDs, 40 sigma levels, sampler solver Heun/Euler and calls, resolution, normalization, postprocess, units.

## Synthetic demonstration in this repository
- `data/demo/manifest.json`: `data_status: synthetic_demo`; available cases, combo, ROI labels and true shape of toy arrays.
- `data/demo/cases/<case>.npz`: `baseline_final`, `perturbed_final`: `[30,12,10]` toy maps.
- `baseline_steps`,`perturbed_steps`: `[5,30,12,10]` toy intermediate maps.
- `baseline_vectors`,`perturbed_vectors`: `[3,5,30,16]` toy feature vectors.
- `data/demo/roi_masks.npz`: named Boolean Output ROI masks `[12,10]`.
- NEVER present toy 5-step / toy 12x10 maps as actual Taiwan EDM inference.

## Calculation contracts
- One case + one Output ROI -> 30 rainfall scalars for baseline, 30 for perturbed.
- `sample_sd` uses sample SD (ddof=1) consistently across API and tests.
- 1D W1 on equal-size empirical distributions = mean absolute difference of independently SORTED samples. Pairing is for member-response/covariance, not for computing W1.
- Paired response `delta_m = perturbed_m - baseline_m`.
- Sample variance identity (same ddof across all terms): `var(P) - var(B) = var(delta) + 2*cov(B, delta)`.
- For ensemble spread, distinguish sample SD change (`sd(P)-sd(B)`) from variance change (`var(P)-var(B)`).
- Step curve: compute W1 between 30 ROI scalars at each denoised-estimate index. Include true sigma and stage metadata.
- Cohort aggregates case-level `delta_mean`, `delta_sd`, `w1`, `delta_tail`; never pool members before computing them.
- Since n=30, report binomial uncertainty or bootstrap where tail estimates matter.
- ROI with zero eligible pixels -> validation error.

## Missing and identity
- Cache keys: `case_id, variable, input_roi_id, magnitude, model_version, seed_set, sampler_spec`; Output ROI is **analysis-time** selector if full maps cached.
- `data_status` required: `synthetic_demo` vs `actual_edm`.
- Manifest must refuse requests outside available coverage.
- Cohort ID is a metadata query / case ID list, NOT a separate generated model.
