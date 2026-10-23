# Taiwan Atmospheric EDM XAI — Claude Code starter

This repository provides **real executable scientific CPU metric/API code, tests, a minimal React UI, and synthetic cache data**. It does NOT contain, train or run your actual EDM or meteorological data. The actual GPU integration is deliberately pending original files and checkpoint.

## First run (Python 3.11+; Windows/macOS/Linux)

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r backend/requirements.txt
python scripts/generate_demo_cache.py
python -m pytest backend/tests -q
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/docs` for API and `http://127.0.0.1:8000/api/case?case_id=20180112` for a **synthetic** result.

Start frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Starting Claude Code

```bash
cd taiwan-edm-xai-claude-starter
claude
```

In Claude Code (slash commands only *inside* interactive session):

```
/plan Audit all specs, confirm demo contracts, and propose the first real EDM adapter milestone. Do not edit code.
/agents
/implement-spec Add a CPU member-response paired scatter view with acceptance tests.
/scientific-review
/diff
/review
```

Read `CLAUDE.md`, `specs/*`, and `docs/PLAN.md`. Verify current Claude Code CLI syntax with `claude --help` as versions may change.

## Offline GPU future integration
See `offline/README.md` and `/edm-cache-audit`. Need actual network, training, inference, dataset stats, checkpoint and sampler CLI/config. No generated demo value is a scientific result.
