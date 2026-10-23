"""Safe, manifest-whitelisted cache loader for synthetic demo.

Later replace file loading implementation with actual versioned Zarr/Parquet
while preserving validation, provenance and API shapes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CacheMiss(LookupError):
    pass


class CacheStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.environ.get("XAI_CACHE_ROOT") or PROJECT_ROOT / "data" / "demo").resolve()
        manifest_path = self.root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"No cache manifest at {manifest_path}. Run python scripts/generate_demo_cache.py")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf8"))
        self.cases = self.manifest["cases"]
        self.combo = self.manifest["perturbation"]
        with np.load(self.root / "roi_masks.npz", allow_pickle=False) as mask_file:
            self.masks = {name: mask_file[name].astype(bool) for name in mask_file.files}

    def validate(self, case_id: str, roi: str, variable: str, input_roi: str, magnitude: float):
        if case_id not in self.cases:
            raise CacheMiss(f"Case {case_id} not in cache")
        if roi not in self.masks:
            raise CacheMiss(f"Output ROI {roi} not cached; available: {list(self.masks)}")
        expected = self.combo
        if (variable != expected["variable"] or input_roi != expected["input_roi"]
                or abs(float(magnitude) - float(expected["magnitude"])) > 1e-8):
            raise CacheMiss("Perturbation not precomputed; available: " + json.dumps(expected))

    def case_arrays(self, case_id: str) -> dict:
        # Whitelist from manifest, never use arbitrary request string as a file path.
        if case_id not in self.cases:
            raise CacheMiss(f"Case {case_id} not cached")
        with np.load(self.root / "cases" / (case_id + ".npz"), allow_pickle=False) as data:
            return {name: data[name] for name in data.files}
