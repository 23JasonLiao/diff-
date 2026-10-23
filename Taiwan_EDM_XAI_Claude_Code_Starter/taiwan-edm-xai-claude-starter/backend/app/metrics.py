"""CPU-only metrics for case-level output ensemble distributions.

All inputs are physical-unit rainfall scalar samples AFTER per-member ROI
aggregation. Here 'spread' means sample SD across members, not pixels.
"""
from __future__ import annotations

import numpy as np


def roi_member_values(maps: np.ndarray, roi_mask: np.ndarray) -> np.ndarray:
    """maps [members,H,W] -> [members], spatial average over Output ROI."""
    maps = np.asarray(maps, dtype=np.float64)
    mask = np.asarray(roi_mask, dtype=bool)
    if maps.ndim != 3 or mask.ndim != 2 or maps.shape[1:] != mask.shape:
        raise ValueError(f"Expected maps [M,H,W] and mask [H,W], got {maps.shape}, {mask.shape}")
    if not np.any(mask):
        raise ValueError("Empty Output ROI")
    samples = maps[:, mask].mean(axis=1)
    if not np.all(np.isfinite(samples)):
        raise ValueError("Non-finite samples")
    return samples


def compare_ensemble(baseline: np.ndarray, perturbed: np.ndarray, threshold: float = 40.0) -> dict:
    """Paired scalar samples with same seed ORDER; 1D W1 uses sorted values."""
    b = np.asarray(baseline, dtype=np.float64)
    p = np.asarray(perturbed, dtype=np.float64)
    if b.ndim != 1 or b.shape != p.shape or len(b) < 2:
        raise ValueError("Require matched 1D ensembles of >=2 members")
    if not np.isfinite(b).all() or not np.isfinite(p).all():
        raise ValueError("Non-finite ensemble")
    delta = p - b
    b_sd = float(np.std(b, ddof=1))
    p_sd = float(np.std(p, ddof=1))
    vdelta = float(np.var(delta, ddof=1))
    cov = float(np.cov(b, delta, ddof=1)[0, 1])
    dvar = float(np.var(p, ddof=1) - np.var(b, ddof=1))
    decomposed = vdelta + 2.0 * cov
    if not np.isclose(dvar, decomposed, atol=1e-9, rtol=1e-8):
        raise AssertionError("Paired sample variance decomposition failed")
    return {
        "n_members": int(len(b)),
        "units": "mm/day",
        "baseline_mean": float(np.mean(b)),
        "perturbed_mean": float(np.mean(p)),
        "delta_mean": float(np.mean(delta)),
        "baseline_sd": b_sd,
        "perturbed_sd": p_sd,
        "delta_sd": p_sd - b_sd,
        "w1": float(np.mean(np.abs(np.sort(b) - np.sort(p)))),
        "threshold": float(threshold),
        "baseline_tail_probability": float(np.mean(b > threshold)),
        "perturbed_tail_probability": float(np.mean(p > threshold)),
        "delta_tail_probability": float(np.mean(p > threshold) - np.mean(b > threshold)),
        "delta_variance": dvar,
        "response_variance": vdelta,
        "baseline_response_cov2": 2.0 * cov,
        "member_responses": [float(x) for x in delta],
        "baseline_member_values": [float(x) for x in b],
        "perturbed_member_values": [float(x) for x in p],
    }


def step_w1_curve(base_steps: np.ndarray, pert_steps: np.ndarray, mask: np.ndarray) -> list[float]:
    """step maps [K,M,H,W] -> one ROI empirical W1 for each K."""
    a = np.asarray(base_steps)
    b = np.asarray(pert_steps)
    if a.ndim != 4 or a.shape != b.shape:
        raise ValueError("Expected matched [K,M,H,W] step arrays")
    return [
        float(np.mean(np.abs(np.sort(roi_member_values(a[k], mask)) - np.sort(roi_member_values(b[k], mask)))))
        for k in range(a.shape[0])
    ]


def layer_step_distance(base_features: np.ndarray, pert_features: np.ndarray) -> list[list[float]]:
    """[layer,step,member,dim] -> [layer,step] mean paired L2 / sqrt(D).

    This is an uncalibrated representation distance, NOT importance/causation.
    """
    b = np.asarray(base_features, dtype=np.float64)
    p = np.asarray(pert_features, dtype=np.float64)
    if b.ndim != 4 or b.shape != p.shape or b.shape[-1] == 0:
        raise ValueError("Expected matched [L,K,M,D] features")
    per_member = np.linalg.norm(p - b, axis=-1) / np.sqrt(b.shape[-1])
    return per_member.mean(axis=2).tolist()


def cohort_aggregate(case_results: list[dict]) -> dict:
    """Aggregate CASE-LEVEL effects; never flatten members across dates."""
    if not case_results:
        raise ValueError("Empty cohort")
    result = {"n_cases": len(case_results), "units": "mm/day"}
    for key in ("delta_mean", "delta_sd", "w1", "delta_tail_probability"):
        vals = np.array([c["metrics"][key] for c in case_results], dtype=float)
        result[key] = {
            "median": float(np.median(vals)),
            "q25": float(np.quantile(vals, 0.25)),
            "q75": float(np.quantile(vals, 0.75)),
        }
    ds = np.array([c["metrics"]["delta_sd"] for c in case_results])
    dm = np.array([c["metrics"]["delta_mean"] for c in case_results])
    result["share_mean_increased"] = float(np.mean(dm > 0))
    result["share_spread_increased"] = float(np.mean(ds > 0))
    curves = np.array([c["step_w1"] for c in case_results], dtype=float)
    result["step_w1_median"] = np.median(curves, axis=0).tolist()
    result["step_w1_q25"] = np.quantile(curves, 0.25, axis=0).tolist()
    result["step_w1_q75"] = np.quantile(curves, 0.75, axis=0).tolist()
    return result
