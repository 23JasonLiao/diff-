# PRD: Physics-informed distribution-centered XAI

## User and intent
An atmospheric scientist chooses a cohort (e.g., winter), one case (date), input physical hypothesis (variable + input ROI + magnitude), and Output ROI. The system compares two already cached 30-member rainfall ensembles generated with matched seeds. The scientist can inspect case detail, cohort median/IQR/consistency, members' paired response, temporal EDM step curve and selected U-Net layer summary.

## Top-level scientific question
For a specified atmospheric condition/perturbation, how does the model's **conditional ensemble distribution over an Output ROI** shift, especially spread? Is its effect reproducible across a physically defined cohort? Where along EDM generation are differences visible? Never claim real atmospheric causality based on model sensitivity alone.

## Terms
- Case = one date + atmospheric condition (e.g., 2018-01-12).
- Cohort = set of case IDs selected using fixed, documented metadata rules (e.g., Dec/Jan/Feb, pre-perturbation rain category).
- Input ROI = mask of coarse atmospheric grid cells altered by perturbation.
- Output ROI = mask of high-resolution grid cells observed after inference; different from Input ROI.
- Member = one spatial rainfall prediction from one seed. Ensemble = 30 members for one case/condition.
- Output distribution = 30 scalar ROI summaries (e.g. spatially averaged rainfall), not all pixels stacked.
- Physical mapping = hypothesized interpretation of inputs and joint conditions; needs domain expert validation.

## Critical questions
RQ1: What are changes in per-case mean, sample standard deviation, 1D W1 and Pr(ROI mean > threshold)?
RQ2: What paired-member response explains the variance difference?
RQ3: Across cohort cases, what is the median, IQR, and sign consistency of effects?
RQ4 (support): How do intermediate denoised estimates and selected-layer feature vectors differ by step/layer?

## User story MVP
1. Scientist chooses `winter`, `2018-01-12`, `q700`, `north`, `+0.5sigma`, `northeast`.
2. CPU reads matching cache records with `data_status` clearly shown.
3. UI shows baseline/perturbed member distribution, mean, spread, W1, tail probability and paired member scatter.
4. UI shows step-W1 and layer-step vector distance (supporting only).
5. Scientist switches to cohort view: medians/IQR, direction consistency, choose outlier case.
6. Changing Output ROI recomputes statistics from cached member maps on CPU without rerunning model.
7. A cache miss shows a transparent `not precomputed` response with supported options.

## Non-goals for MVP
- Unlimited on-demand input masks/magnitudes/physical multivariable perturbations.
- CPU EDM sampling/inference or runtime activation patching.
- Natural-language LLM interpretations pretending to be physical truth.
- Replacing calibration/forecast verification with spread shift alone.
- Training new EDM architecture or reimplementing original network.

## Definition of success
- All scientific metrics are unit-tested and show exact sample counts.
- Synthetic demonstration is marked synthetic; no actual EDM claims without provenance.
- UI/API runs with CPU only; no torch/CUDA in online code.
- A single case and cohort both use the same output ROI semantics.
- Missing data never produces inferred surrogate model outputs.
