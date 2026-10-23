---
name: implement-spec
description: Implement one scoped feature in the Taiwan EDM XAI codebase based on specs, with tests and code review. Use when user asks to implement an API/UI/cache feature or slash command /implement-spec.
argument-hint: "feature-name"
---
1. Read `CLAUDE.md`, `specs/PRD.md`, `specs/CACHE_CONTRACT.md`, and `specs/ACCEPTANCE.md`.
2. Find the smallest acceptance test relevant to the requested feature: `$ARGUMENTS`.
3. Write a concise plan describing impacted files and exact input/output shapes before editing.
4. Add a failing test for scientific behavior. Implement one vertical slice, not several unreviewed features.
5. Run `python -m pytest backend/tests -q`; if frontend is modified, run `npm run build` in `frontend` (after dependencies installed).
6. Request `scientific-reviewer` for math changes and `qa-reviewer` for API/cache changes.
7. Summarize edits, test output, known limitations and update `docs/PLAN.md`. Never call demo data actual EDM results.
