# Claude Code essentials (verify version with `claude --help`)

Terminal shell (outside Claude session):
- `claude` -> start interactive session.
- `claude "Read CLAUDE.md and propose phase 1"` -> launch with initial request.
- `claude -p "Summarize the API files"` -> print-and-exit non-interactively.
- `claude -c` -> resume most recent current-directory conversation.
- `claude -r "session-name"` -> resume named session.
- `claude --permission-mode plan` -> start read-only planning.
- `claude mcp add --transport stdio playwright -- npx -y @playwright/mcp@latest` -> OPTIONAL browser MCP (npx + network/Node needed).
- `claude mcp list` -> inspect configured MCPs.
- `claude update` -> update Claude Code.

Inside Claude interactive session (slash commands):
- `/init` -> create starter CLAUDE.md if missing; this repo already has curated CLAUDE.md; REVIEW before replacing.
- `/plan` -> read-only design and risk/acceptance pass.
- `/agents` -> inspect/discover subagents.
- `/skills` -> inspect/discover skills.
- `/implement-spec` `/edm-cache-audit` `/scientific-review` -> project-specific skills.
- `/mcp` -> MCP connection status/authentication.
- `/permissions` -> policy and approvals.
- `/hooks` -> inspect hooks loaded from settings.
- `/diff` -> inspect edits.
- `/review` `/security-review` -> local read-only review.
- `/compact` -> compact context while preserving project files.
- `/clear` -> fresh conversation for next milestone.
- `/doctor` -> diagnose Claude Code setup.
- `/model` `/effort` -> adjust model / reasoning budget.

DO NOT use `--dangerously-skip-permissions` for this project: data/checkpoints are valuable. Keep one writing agent per overlapping file ownership scope. Let other agents independently review.
