"""Make clearly SYNTHETIC tiny arrays for local end-to-end UI demonstration.

Not Taiwan geographic data, not atmospheric model outputs, not actual EDM.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "demo"
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "cases").mkdir(exist_ok=True)

H, W = 12, 10
mask_ne = np.zeros((H, W), dtype=bool)
mask_ne[:6, 5:] = True
mask_n = np.zeros((H, W), dtype=bool)
mask_n[:6, :] = True
mask_all = np.ones((H, W), dtype=bool)
np.savez_compressed(DEST / "roi_masks.npz", northeast=mask_ne, north=mask_n, all=mask_all)

cases = ["20171220", "20180103", "20180112", "20180204"]
step_sigma = [80.0, 15.0, 3.0, 0.5, 0.0]  # synthetic labels, not an actual EDM schedule
for idx, case_id in enumerate(cases):
    rng = np.random.default_rng(20261022 + idx)
    shared = rng.normal(0, 1, (30, 1, 1))
    spatial = rng.uniform(0, 2, (1, H, W))
    baseline = (14 + 6 * idx + 8 * shared + spatial + rng.normal(0, 1.5, (30, H, W))).clip(0)
    response = 1.5 + (1.2 + idx * 0.2) * shared + rng.normal(0, 0.6, (30, 1, 1))
    perturbed = (baseline + response + 0.7 * mask_ne).clip(0)
    # progress 0->1 just displays invented toy intermediate distributions
    bsteps = np.stack([(0.25 + 0.75 * k / 4) * baseline for k in range(5)])
    psteps = np.stack([bsteps[k] + (0.1 + 0.9 * k / 4) * (perturbed - baseline) for k in range(5)])
    bvec = rng.normal(size=(3, 5, 30, 16))
    pvec = bvec + rng.normal(size=(3, 5, 30, 16)) * np.linspace(0.02, 0.5, 5)[None, :, None, None]
    np.savez_compressed(
        DEST / "cases" / (case_id + ".npz"),
        baseline_final=baseline.astype("float32"), perturbed_final=perturbed.astype("float32"),
        baseline_steps=bsteps.astype("float32"), perturbed_steps=psteps.astype("float32"),
        baseline_vectors=bvec.astype("float32"), perturbed_vectors=pvec.astype("float32"),
    )
manifest = {
    "schema_version": "0.1-demo",
    "data_status": "synthetic_demo",
    "warning": "SYNTHETIC TEACHING DATA ONLY. Not actual Taiwan geography, checkpoint, atmospheric fields, or EDM inference.",
    "cases": cases,
    "cohorts": {"winter": cases},
    "perturbation": {"variable": "q700", "input_roi": "north", "magnitude": 0.5},
    "metadata": {
        "checkpoint": None,
        "origin": "numpy synthetic generator: scripts/generate_demo_cache.py",
        "map_shape": [H, W],
        "step_metadata": [{"index": k, "sigma": float(v), "source": "synthetic_progress_only"} for k, v in enumerate(step_sigma)],
        "layer_ids": ["encoder_toy", "middle_toy", "decoder_toy"],
        "seeds": [int(i) for i in range(30)],
        "units": "mm/day (synthetic numerical scale)",
    },
}
(DEST / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
print(f"Synthetic demo cache generated at {DEST}")
