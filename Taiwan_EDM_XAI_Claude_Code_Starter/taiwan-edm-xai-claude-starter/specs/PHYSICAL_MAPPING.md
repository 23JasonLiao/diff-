# Physical mapping / cohort study specification

## Notation
- An atmospheric 'physical concept' is a domain hypothesis. Its implementation is an explicit transform or metadata rule, not a causal proof.
- `C(date)` contains q700, t2m, u, v, msl, tp, landmask in explicit channel order and units.
- User specifies `physical_concept`, `variable(s)`, `input_roi_id`, `magnitude`, `case/cohort`, `output_roi_id`.

## Pilot physical concepts
1. `midlevel_moisture`: q700 mean/anomaly within an input region, seasonal/cohort training reference. Perturb q700 alone.
2. `circulation_background`: wind vector/strength/direction or pressure pattern as case metadata; exact u/v pressure levels must be confirmed.
3. `joint_moisture_wind` (phase 2): perturb physically coherent q700 and compatible wind variables together; log numerical changes and distinguish interaction from additive separate effects.
4. `coarse_precipitation`: tp. Must specify reconstruction baseline handling (`condition_only`, `baseline_only`, `end_to_end`) before analyses.

## Cohort selection: no post-treatment leakage
- Cohort is a list of case dates chosen from ORIGINAL measured/pre-perturbation inputs and/or truth if using evaluation cohorts.
- If cohort selected by true rainfall at Output ROI, document that selection may depend on truth and will not be available for operational inference without truth.
- Avoid selecting cohorts using the PERTURBED outcome when claiming general behavior: selection must be applied consistently and explained.
- E.g. `winter` = Dec/Jan/Feb plus region-specific original high rainfall threshold if appropriate; store exact threshold and train/validation provenance.

## Member response and dispersion
For ROI-mean rainfall scalars `B_m`, `P_m` aligned by identical seed m:
- `delta_m=P_m-B_m`
- Spread shift is `sample_sd(P)-sample_sd(B)` in mm/day.
- Exact variance decomposition (sample ddof=1): `var(P)-var(B)=var(delta)+2cov(B,delta)` in (mm/day)^2.
- This identity explains HOW paired numerical changes yield dispersion, not WHAT physical mechanism caused them.
- Compare concepts across cohorts using median/IQR of per-case effects and direction consistency; report sample-size uncertainty.

## Deliverable view
A Physical Concept Explorer offers: select input physical concept -> fixed perturbation cache key -> output ROI and cohort -> distribution shift + member-response scatter + subgroup comparisons. GPU computes any new neural-network counterfactual; CPU only looks up already cached ones.
