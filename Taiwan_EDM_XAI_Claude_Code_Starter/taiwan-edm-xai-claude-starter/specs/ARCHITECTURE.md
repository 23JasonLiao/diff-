# Architecture: GPU offline vs CPU online

```
          OFFLINE GPU (H200 or other supported cluster)
   Checkpoint + ERA cases + training stats + masks
                         |
      perturbation coverage grid (case x variable x input ROI x magnitude)
                         |
        paired same-seed baseline & perturbed EDM inference
        final member maps + denoised estimates by saved step
        selected canonical layer hooks (raw map -> compact vector)
                         |
           immutable versioned cache + metadata + manifest
                         |
          CPU-only FastAPI (NumPy, SciPy optional)
                |                  |
           Case stats         Cohort aggregation
                \                  /
                      React UI
```

## GPU workflow
- Dry-run with one case, one variable and 2-3 seeds; inspect shapes and units manually.
- Separate `offline/adapters/` to import true network, data loader, sampler and postprocess. Do NOT assume generic EDM is bitwise compatible.
- Set seeds and sampler configuration deterministically; if stochastic churn is enabled, pair per-step noise too.
- Cache `final_rainfall[member,H,W]`; `step_denoised_rainfall[step,member,H,W]` where each saved point has a specified sigma and predictor/corrector call semantics; `features[layer,step,member,D]` with canonical hook IDs.
- Save true physical mm/day, plus original model representation metadata for audit.
- Prefer chunked Zarr or per-key compressed NumPy for prototyping. Write atomically with checksums.
- Store output maps if Output ROI should be editable online; a single ROI scalar cache is not enough.
- Build coverage index before precomputation: combinatorial explosion is real. `Ncases * Nvariables * Nmagnitudes * NinputROIs` full ensemble runs.
- Example 30*40*112*72*2 bytes ~= 19.4 MB per condition just for step rain maps in float16; actual compression, call count, and feature cost vary.

## CPU workflow
- API may load fixed region masks or arbitrary polygon rasterized onto cached grid; compute per-member ROI scalar then ensemble stats.
- Cohort defined by case IDs and metadata. Cohort summary uses per-case effects, not pooled member values.
- Layer vectors should be normalized with fixed calibration transform to compare across layers, or separately labeled as non-comparable raw distances.
- No runtime calls to torch CUDA or trained U-Net. Cache miss -> 404 with available combinations.
- Keep baseline cache shared across perturbation options (do not duplicate baseline if not needed).

## Physical mapping policies
- `q700` is mid-tropospheric moisture, not the total atmospheric column.
- `u,v` need exact pressure level before claims about moisture transport; divergence or advection requires grid spacing and level consistency.
- `t2m` alone cannot identify vertical instability.
- Terrain effect requires supporting elevation/orographic information.
- `tp` modifies the conditional input AND may enter baseline reconstruction. Specify `condition_only`, `baseline_only`, or `end_to_end` mode when that channel is perturbed.

## Security and usability
- API restricts cache keys/paths to whitelist in manifest, no user-provided filesystem paths.
- Demo inputs always clearly labeled synthetic.
- No credential files, huge datasets or checkpoints in Git.
