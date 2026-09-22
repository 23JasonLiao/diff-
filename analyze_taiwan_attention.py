#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze saved attention matrices from extract_taiwan_edm_features.py.

Produces simple quantitative summaries that are useful for physics-oriented
hypotheses. This script intentionally avoids claiming causality.
"""

import argparse
import torch


def expected_attention_distance(A, H, W):
    """A: [B, heads, N, N], returns [B, heads] mean expected grid distance."""
    device = A.device
    yy, xx = torch.meshgrid(torch.arange(H, device=device), torch.arange(W, device=device), indexing='ij')
    coords = torch.stack([yy.flatten(), xx.flatten()], dim=1).float()  # [N,2]
    dist = torch.cdist(coords, coords)  # [N,N]
    return (A.float() * dist).sum(dim=-1).mean(dim=-1)


def attention_entropy(A, eps=1e-12):
    """Mean query entropy per head. A: [B,heads,N,N]."""
    P = A.float().clamp_min(eps)
    return (-(P * P.log()).sum(dim=-1)).mean(dim=-1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--features', required=True)
    p.add_argument('--sigma', required=True)
    p.add_argument('--height', type=int, default=14)
    p.add_argument('--width', type=int, default=9)
    args = p.parse_args()

    obj = torch.load(args.features, map_location='cpu')
    item = obj['per_sigma'][str(float(args.sigma))]
    if 'attention' not in item:
        raise KeyError('No attention matrix saved for this sigma.')
    A = item['attention'].float()

    print('attention shape:', tuple(A.shape))
    print('row-sum mean (should be ~1):', A.sum(dim=-1).mean().item())
    print('expected grid distance per head:', expected_attention_distance(A, args.height, args.width))
    print('entropy per head:', attention_entropy(A))


if __name__ == '__main__':
    main()
