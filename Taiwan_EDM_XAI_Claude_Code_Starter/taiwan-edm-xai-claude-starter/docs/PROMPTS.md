# Ready-to-paste Claude Code prompts, one milestone at a time

## Initial no-edit architecture pass
/plan Read CLAUDE.md, specs/PRD.md, specs/ARCHITECTURE.md, specs/CACHE_CONTRACT.md, specs/PHYSICAL_MAPPING.md and specs/ACCEPTANCE.md. Inspect current tests and data/demo. Present the smallest safe roadmap from this synthetic CPU demo to actual Taiwan EDM cache. Do not edit files, do not generate scientific claims, do not reimplement my EDM.

## Actual model audit (after copying reference source/checkpoint description, not binary, into a safe workspace)
Use edm-integrator as a read-only independent agent. Inspect my actual Network, TrainDiffusion, Inference, dataset preprocessing and checkpoint metadata. Produce a source-grounded shape/normalization/seeding/sampling-step report with file:line references. If a required file is missing, write down exactly which one is missing. Do not modify the model.

## Frozen numerical golden tests
/implement-spec Write tests for a no-op perturbation that must exactly reproduce baseline seeds, numerical rainfall conversion, sample layout [M,H,W], and step denoised estimates. Use a single real case, 2 seeds first, and compare to existing inference. Ask scientific-reviewer to review; do not start a whole precompute batch.

## GPU offline adapter
/implement-spec Implement offline GPU adapter ONLY after golden tests and review. Preserve trained weights and the existing inference algorithm. Support one case, one q700/north/+0.5sigma perturbation with paired seeds; export versioned metadata and small cache. Include run CLI for H200, exact checkpoint/data paths as flags rather than constants. Do not change backend/frontend. Test and report.

## Cache validation
/edm-cache-audit Validate actual checkpoint SHA256, data dates, normalization stats, every paired seed/noise stream, solver/sigma call semantics, 30 member counts and physical units. Mark cache actual only if all provenance and acceptance checks pass.

## Expand CPU XAI
/implement-spec Build member-response scatter/variance decomposition UI and tests. Read scientific metric specs; no torch in backend. Use 2018-01-12 demo data but label every result synthetic. Include a missing-cache error state.

## Physical mapping and cohort
/implement-spec Add physical-concept selector with documented physical assumptions, cohort subgroups determined from PRE-perturbation metadata, per-case effect statistics, IQR and consistency. Refuse any input perturbation absent from cache, do not claim causal mechanism.

## Read-only gate before each merge
Ask scientific-reviewer and qa-reviewer, independently and read-only, to report P0 and P1 issues. Fix only verified issues; run pytest/backend, UI build, and an end-to-end API demo. Summarize exact pass/fail evidence. Avoid large unrelated refactors.
