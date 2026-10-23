"""Best-effort Python syntax warning after Write/Edit, does not rewrite files."""
import json
import os
import py_compile
import sys
from pathlib import Path

try:
    payload = json.load(sys.stdin)
    ti = payload.get("tool_input", {})
    target = ti.get("file_path", "")
    if target.endswith(".py"):
        repo = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
        path = Path(target).resolve()
        if path.is_relative_to(repo) and path.exists():
            py_compile.compile(str(path), doraise=True)
except (py_compile.PyCompileError, Exception) as exc:
    print(f"[Python syntax/verification warning] {exc}", file=sys.stderr)
