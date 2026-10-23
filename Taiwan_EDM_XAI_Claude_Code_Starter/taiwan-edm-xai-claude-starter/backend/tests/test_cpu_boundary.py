import ast
from pathlib import Path


def test_backend_does_not_import_gpu_or_network():
    base = Path(__file__).resolve().parents[1] / "app"
    for file in base.rglob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf8"))
        names = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names.extend(alias.name for alias in n.names)
            if isinstance(n, ast.ImportFrom) and n.module:
                names.append(n.module)
        for name in names:
            assert name.split(".")[0] not in {"torch", "cupy", "tensorflow", "Network", "TrainDiffusion"}, (file, name)
