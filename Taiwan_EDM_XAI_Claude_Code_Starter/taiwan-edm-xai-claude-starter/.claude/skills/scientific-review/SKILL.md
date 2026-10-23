---
name: scientific-review
description: Run a reproducible scientific review of output ensemble distribution and member-response calculations. Use for reviewing formula implementations, cohort logic, or XAI results.
---
- Verify one spatial scalar per member before ensemble summary.
- Verify 30 vs 30 paired seed identity and separated independent W1 matching.
- Check sample SD and sample covariance `ddof=1` consistently.
- Check `Var(P)-Var(B)=Var(delta)+2Cov(B,delta)` numerically.
- Check cohort aggregates per-case metric vectors, not pooled case/member samples.
- Check missing ROI, units and negative rainfall handling; mention uncertainty with 30 members.
- Check physical hypotheses are labeled as model input sensitivity, not causal physical laws.
- Report exact failing tests, expected calculation and needed fix. Do not alter scientific definitions without user approval.
