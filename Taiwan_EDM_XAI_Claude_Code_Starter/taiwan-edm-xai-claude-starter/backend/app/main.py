"""CPU-only XAI API; all EDM inference is done offline."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .metrics import cohort_aggregate, compare_ensemble, layer_step_distance, roi_member_values, step_w1_curve
from .store import CacheMiss, CacheStore

app = FastAPI(title="Taiwan EDM CPU-only XAI (starter)", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET"], allow_headers=["*"])


def store():
    try:
        return CacheStore()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok", "runtime": "cpu-only", "edm_inference": False}


@app.get("/api/options")
def options():
    s = store()
    return {
        "data_status": s.manifest["data_status"],
        "warning": s.manifest["warning"],
        "cohorts": s.manifest["cohorts"],
        "cases": s.cases,
        "output_rois": list(s.masks),
        "perturbations": [s.combo],
        "metadata": s.manifest["metadata"],
    }


def analyze_case(s: CacheStore, case_id: str, output_roi: str, threshold: float) -> dict:
    arrays = s.case_arrays(case_id)
    mask = s.masks[output_roi]
    b = roi_member_values(arrays["baseline_final"], mask)
    p = roi_member_values(arrays["perturbed_final"], mask)
    metrics = compare_ensemble(b, p, threshold)
    return {
        "case_id": case_id,
        "data_status": s.manifest["data_status"],
        "output_roi": output_roi,
        "metrics": metrics,
        "step_w1": step_w1_curve(arrays["baseline_steps"], arrays["perturbed_steps"], mask),
        "layer_step_distance": layer_step_distance(arrays["baseline_vectors"], arrays["perturbed_vectors"]),
        "step_metadata": s.manifest["metadata"]["step_metadata"],
        "layer_ids": s.manifest["metadata"]["layer_ids"],
        "interpretation_note": "Layer vector distance indicates representation difference, not causal importance.",
    }


@app.get("/api/case")
def case(
    case_id: str,
    variable: str = "q700",
    input_roi: str = "north",
    magnitude: float = 0.5,
    output_roi: str = "northeast",
    threshold: float = Query(40.0, ge=0),
):
    s = store()
    try:
        s.validate(case_id, output_roi, variable, input_roi, magnitude)
        return analyze_case(s, case_id, output_roi, threshold)
    except CacheMiss as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/cohort")
def cohort(
    cohort: str = "winter",
    variable: str = "q700",
    input_roi: str = "north",
    magnitude: float = 0.5,
    output_roi: str = "northeast",
    threshold: float = Query(40.0, ge=0),
):
    s = store()
    if cohort not in s.manifest["cohorts"]:
        raise HTTPException(404, f"Cohort {cohort} not found")
    ids = s.manifest["cohorts"][cohort]
    try:
        for case_id in ids:
            s.validate(case_id, output_roi, variable, input_roi, magnitude)
        results = [analyze_case(s, cid, output_roi, threshold) for cid in ids]
    except CacheMiss as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "cohort": cohort,
        "case_ids": ids,
        "data_status": s.manifest["data_status"],
        "output_roi": output_roi,
        "summary": cohort_aggregate(results),
        "cases": [{"case_id": c["case_id"], "delta_mean": c["metrics"]["delta_mean"], "delta_sd": c["metrics"]["delta_sd"]} for c in results],
        "warning": s.manifest["warning"],
    }
