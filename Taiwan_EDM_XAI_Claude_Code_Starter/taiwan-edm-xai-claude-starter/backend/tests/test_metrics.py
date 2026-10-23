import numpy as np
import pytest

from app.metrics import cohort_aggregate, compare_ensemble, roi_member_values


def test_zero_perturbation_all_effects_zero():
    x = np.arange(1.0, 31.0)
    r = compare_ensemble(x, x)
    for key in ("delta_mean", "delta_sd", "w1", "delta_tail_probability", "delta_variance", "response_variance"):
        assert r[key] == pytest.approx(0.0)


def test_constant_shift_preserves_spread_and_w1():
    x = np.linspace(5, 25, 30)
    r = compare_ensemble(x, x + 7)
    assert r["delta_mean"] == pytest.approx(7)
    assert r["delta_sd"] == pytest.approx(0)
    assert r["w1"] == pytest.approx(7)
    assert r["delta_variance"] == pytest.approx(0)


def test_variance_decomposition_with_heterogeneous_responses():
    b = np.linspace(1, 40, 30)
    p = b + b * 0.5 + np.sin(b)
    r = compare_ensemble(b, p)
    assert r["delta_variance"] == pytest.approx(r["response_variance"] + r["baseline_response_cov2"])


def test_spatial_heterogeneity_does_not_fake_member_spread():
    base = np.array([[[-1, 1], [0, 0]]] * 30, dtype=float)
    mask = np.ones((2, 2), dtype=bool)
    members = roi_member_values(base, mask)
    assert np.std(members, ddof=1) == 0  # each member has the same ROI average
    assert roi_member_values(base + 5, mask).shape == (30,)


def test_roi_empty_is_error():
    with pytest.raises(ValueError, match="Empty"):
        roi_member_values(np.zeros((30, 2, 2)), np.zeros((2, 2), dtype=bool))


def test_cohort_aggregates_case_effects_not_member_pooling():
    a = {"metrics": {"delta_mean": -100, "delta_sd": 0, "w1": 100, "delta_tail_probability": -0.2}, "step_w1": [0, 2]}
    b = {"metrics": {"delta_mean": 2, "delta_sd": 4, "w1": 2, "delta_tail_probability": 0.2}, "step_w1": [0, 10]}
    c = {"metrics": {"delta_mean": 3, "delta_sd": 5, "w1": 3, "delta_tail_probability": 0.3}, "step_w1": [0, 12]}
    r = cohort_aggregate([a, b, c])
    assert r["delta_mean"]["median"] == 2
    assert r["step_w1_median"] == [0, 10]
    assert r["share_mean_increased"] == pytest.approx(2 / 3)
