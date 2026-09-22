#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controlled DiffuseSeg-style feature extraction for the Taiwan rainfall EDM.

Key idea:
    DiffuseSeg: x0 -> q(x_t|x0) -> frozen DDPM U-Net -> F_{t,l}
    Ours:       x0 -> x_sigma=x0+sigma*eps -> frozen EDM U-Net -> F_{sigma,l}

This script deliberately uses ONE fixed epsilon for all sigma values so that
changes in features are attributable to noise level rather than a different
noise realization.
"""

import argparse
import importlib
from pathlib import Path
import math

import torch
from torch.utils.data import DataLoader

from DatasetTaiwanERA_IDW_tp_bilinear import TaiwanERAPrecipDataset, load_stats


def parse_csv_floats(text):
    return [float(x.strip()) for x in text.split(',') if x.strip()]


def parse_csv_strings(text):
    return [x.strip() for x in text.split(',') if x.strip()]


def unwrap_state_dict(obj):
    """Accept a raw state_dict or common checkpoint dictionaries."""
    if isinstance(obj, dict):
        for key in ("state_dict", "model", "network", "ema"):
            if key in obj and isinstance(obj[key], dict):
                return obj[key]
    return obj


def strip_module_prefix(state):
    if state and all(k.startswith("module.") for k in state.keys()):
        return {k[len("module."):]: v for k, v in state.items()}
    return state


class ActivationCollector:
    def __init__(self):
        self.features = {}
        self.handles = []

    def add(self, name, module):
        def hook(_module, _inputs, output):
            self.features[name] = output.detach().float().cpu()
        self.handles.append(module.register_forward_hook(hook))

    def clear(self):
        self.features = {}

    def close(self):
        for h in self.handles:
            h.remove()
        self.handles = []


class QKVCollector:
    """Capture qkv projection output from one attention-enabled UNetBlock."""
    def __init__(self, block):
        if getattr(block, "num_heads", 0) <= 0 or not hasattr(block, "qkv"):
            raise ValueError("Selected block is not attention-enabled.")
        self.block = block
        self.qkv = None
        self.handle = block.qkv.register_forward_hook(self._hook)

    def _hook(self, _module, _inputs, output):
        self.qkv = output.detach().float().cpu()

    def attention_matrix(self):
        if self.qkv is None:
            return None
        # Matches Network.py:
        # q,k,v = qkv.reshape(B*H, C/H, 3, N).unbind(2)
        qkv = self.qkv
        B, threeC, H, W = qkv.shape
        C = threeC // 3
        heads = int(self.block.num_heads)
        head_ch = C // heads
        N = H * W
        q, k, _v = qkv.reshape(B * heads, head_ch, 3, N).unbind(2)
        scores = torch.einsum("ncq,nck->nqk", q, k / math.sqrt(head_ch))
        weights = scores.softmax(dim=2)
        return weights.reshape(B, heads, N, N)

    def clear(self):
        self.qkv = None

    def close(self):
        self.handle.remove()


def build_model(args, dataset, device):
    network_mod = importlib.import_module(args.network_module)

    model_kwargs = dict(
        model_channels=args.model_channels,
        channel_mult=[int(x) for x in args.channel_mult.split(',')],
        num_blocks=args.num_blocks,
        dropout=args.dropout,
    )

    # Pass use_attention only if you have applied the ablation patch below.
    if args.use_attention_flag is not None:
        model_kwargs["use_attention"] = bool(args.use_attention_flag)

    net = network_mod.EDMPrecond(
        dataset.img_resolution,
        dataset.num_input_channels + dataset.target_channels,
        dataset.target_channels,
        label_dim=2,
        **model_kwargs,
    ).to(device)

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    state = strip_module_prefix(unwrap_state_dict(ckpt))
    missing, unexpected = net.load_state_dict(state, strict=False)
    if missing or unexpected:
        print("[checkpoint warning] missing:", missing)
        print("[checkpoint warning] unexpected:", unexpected)
        if args.strict_checkpoint:
            raise RuntimeError("Checkpoint/model architecture mismatch.")

    net.eval()
    return net


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True)
    p.add_argument("--stats", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--network-module", default="networkold")
    p.add_argument("--resolution", default="8km", choices=["1km", "5km", "8km"])
    p.add_argument("--date", required=True, help="YYYYMMDD; a single controlled event")
    p.add_argument("--sigmas", default="0.03,0.1,0.3,1.0,3.0")
    p.add_argument("--layers", default="14x9_block2,28x18_block2,56x36_block2,112x72_block2")
    p.add_argument("--attention-block", default="14x9_in0")
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--model-channels", type=int, default=64)
    p.add_argument("--channel-mult", default="1,2,3,4")
    p.add_argument("--num-blocks", type=int, default=2)
    p.add_argument("--dropout", type=float, default=0.10)
    p.add_argument("--use-attention-flag", type=int, choices=[0, 1], default=None,
                   help="Only use after adding use_attention to Network.py.")
    p.add_argument("--strict-checkpoint", action="store_true")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    stats = load_stats(args.stats)
    dataset = TaiwanERAPrecipDataset(
        data_dir=args.data_dir,
        resolution=args.resolution,
        start_date=args.date,
        end_date=args.date,
        condition_vars=["q700", "t2m", "u", "v", "msl", "tp"],
        use_mask=True,
        target_transform="log1p",
        stats=stats,
    )
    loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)
    batch = next(iter(loader))

    condition = batch["inputs"].to(device)
    x0 = batch["targets"].to(device)  # normalized log-residual target
    labels = torch.stack((batch["year"].to(device), batch["doy"].to(device)), dim=1)

    net = build_model(args, dataset, device)
    core_unet = net.model

    print("\nAvailable decoder blocks:")
    for name, module in core_unet.dec.items():
        print(f"  {name:20s} -> {module.__class__.__name__}, heads={getattr(module, 'num_heads', '-')}")

    requested_layers = parse_csv_strings(args.layers)
    collector = ActivationCollector()
    for name in requested_layers:
        if name not in core_unet.dec:
            raise KeyError(f"Decoder block '{name}' not found. Inspect printed names above.")
        collector.add(name, core_unet.dec[name])

    qkv_collector = None
    if args.attention_block:
        if args.attention_block not in core_unet.dec:
            raise KeyError(f"Attention block '{args.attention_block}' not found")
        block = core_unet.dec[args.attention_block]
        if getattr(block, "num_heads", 0) > 0:
            qkv_collector = QKVCollector(block)
        else:
            print(f"[warning] {args.attention_block} has no active self-attention")

    # SAME epsilon for all sigmas: critical controlled comparison.
    gen = torch.Generator(device=device)
    gen.manual_seed(args.seed)
    eps = torch.randn(x0.shape, generator=gen, device=device, dtype=x0.dtype)

    out = {
        "date": args.date,
        "seed": args.seed,
        "sigmas": parse_csv_floats(args.sigmas),
        "layer_names": requested_layers,
        "x0": x0.detach().float().cpu(),
        "condition": condition.detach().float().cpu(),
        "labels": labels.detach().float().cpu(),
        "epsilon": eps.detach().float().cpu(),
        "per_sigma": {},
    }

    with torch.no_grad():
        for sigma_value in out["sigmas"]:
            collector.clear()
            if qkv_collector is not None:
                qkv_collector.clear()

            sigma = torch.full((x0.shape[0],), sigma_value, device=device, dtype=x0.dtype)
            x_sigma = x0 + sigma.reshape(-1, 1, 1, 1) * eps

            denoised = net(x_sigma, sigma, condition, labels)

            item = {
                "x_sigma": x_sigma.detach().float().cpu(),
                "denoised": denoised.detach().float().cpu(),
                "features": {k: v.clone() for k, v in collector.features.items()},
            }
            if qkv_collector is not None:
                A = qkv_collector.attention_matrix()
                if A is not None:
                    item["attention"] = A.half()  # [B, heads, N, N]
            out["per_sigma"][str(sigma_value)] = item

            print(f"\nsigma={sigma_value:g}")
            for name, feat in item["features"].items():
                print(f"  {name}: {tuple(feat.shape)}")
            if "attention" in item:
                print("  attention:", tuple(item["attention"].shape))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    torch.save(out, args.output)
    print("\nSaved:", args.output)

    collector.close()
    if qkv_collector is not None:
        qkv_collector.close()
    dataset.close()


if __name__ == "__main__":
    main()
