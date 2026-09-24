#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author-style Taiwan precipitation EDM training with optional self-attention.

Based on:
  409262308/IDW_loss dev/
  TrainDiffusion_Taiwan_Bilinear_DDP_AuthorStyle.py

Key change:
  --use-attention  : train the original CNN U-Net + self-attention model
  --no-attention   : train the CNN-only U-Net (attention modules are not created)

The two experiments should be trained separately from scratch with otherwise
identical settings.

8-GPU example:
  torchrun --standalone --nproc_per_node=8 \
    TrainDiffusion_Taiwan_Bilinear_DDP_AuthorStyle_attention_ablation.py \
    --data-dir /home/wuyizhen61/IDW_loss/ERA_dataset \
    --resolution 8km \
    --train-start 19600101 \
    --train-end 20141125 \
    --val-start 20141126 \
    --val-end 20171213 \
    --epochs 150 \
    --batch-size 16 \
    --lr 1e-4 \
    --accum 2 \
    --num-workers 4 \
    --model-channels 64 \
    --channel-mult 1,2,3,4 \
    --num-blocks 2 \
    --attn-resolutions 32,16,8 \
    --dropout 0.10 \
    --no-attention \
    --output-dir ./outputs_taiwan_8km_bilinear_noattn_150
"""

import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

# Modified: use the patched network that supports use_attention=True/False.
import Network_attention_ablation as networkold

from DatasetTaiwanERA_IDW_tp_bilinear import (
    TaiwanERAPrecipDataset,
    compute_stats,
    load_stats,
    save_stats,
)


# -----------------------------------------------------------------------------
# Loss class taken from EDS_Diffusion/loss.py (unchanged from GitHub source).

class EDMLoss:
    def __init__(self, P_mean=-1.2, P_std=1.2, sigma_data=1.0):
        self.P_mean = P_mean
        self.P_std = P_std
        self.sigma_data = sigma_data

    def __call__(
        self,
        net,
        images,
        conditional_img=None,
        labels=None,
        augment_pipe=None,
    ):
        rnd_normal = torch.randn(
            [images.shape[0], 1, 1, 1], device=images.device
        )
        sigma = (rnd_normal * self.P_std + self.P_mean).exp()
        weight = (
            (sigma ** 2 + self.sigma_data ** 2)
            / (sigma * self.sigma_data) ** 2
        )
        y, augment_labels = (
            augment_pipe(images)
            if augment_pipe is not None
            else (images, None)
        )
        n = torch.randn_like(y) * sigma
        D_yn = net(
            y + n,
            sigma,
            conditional_img,
            labels,
            augment_labels=augment_labels,
        )
        loss = weight * ((D_yn - y) ** 2)
        return loss


# -----------------------------------------------------------------------------
# DDP helpers. No special 8-GPU rewrite is needed: torchrun sets WORLD_SIZE=8.

def setup_distributed():
    if "RANK" not in os.environ or "WORLD_SIZE" not in os.environ:
        raise RuntimeError(
            "This script must be launched with torch.distributed.run/torchrun."
        )

    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    local_rank = int(os.environ.get("LOCAL_RANK", 0))

    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)
    dist.init_process_group(backend="nccl", init_method="env://")
    dist.barrier(device_ids=[local_rank])
    return rank, world_size, local_rank, device


def cleanup_distributed():
    if dist.is_available() and dist.is_initialized():
        dist.barrier(device_ids=[torch.cuda.current_device()])
        dist.destroy_process_group()


def reduce_mean(value, device, world_size):
    tensor = torch.tensor(float(value), dtype=torch.float64, device=device)
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    tensor /= world_size
    return float(tensor.item())


# -----------------------------------------------------------------------------
# Training step. Intentionally kept consistent with the GitHub author-style file.

def training_step(
    model,
    loss_fn,
    optimiser,
    data_loader,
    scaler,
    step,
    world_size,
    accum=4,
    writer=None,
    device="cuda",
    rank=0,
):
    """Function for a single training epoch."""

    model.train()
    optimiser.zero_grad(set_to_none=True)
    iterator = tqdm(
        total=len(data_loader),
        dynamic_ncols=True,
        disable=(rank != 0),
    )
    if rank == 0:
        iterator.set_description(f"Train :: Epoch: {step}")

    epoch_losses = []
    step_loss = 0.0

    for i, batch in enumerate(data_loader):
        if rank == 0:
            iterator.update(1)

        image_input = batch["inputs"].to(device, non_blocking=True)
        image_output = batch["targets"].to(device, non_blocking=True)
        year = batch["year"].to(device, non_blocking=True)
        day = batch["doy"].to(device, non_blocking=True)
        condition_params = torch.stack((year, day), dim=1)

        with torch.cuda.amp.autocast():
            loss = loss_fn(
                net=model,
                images=image_output,
                conditional_img=image_input,
                labels=condition_params,
            )
            loss = torch.mean(loss)

        # Kept identical to the source trainer: no extra /accum scaling here.
        scaler.scale(loss).backward()
        step_loss += loss.item()

        if (i + 1) % accum == 0:
            scaler.step(optimiser)
            scaler.update()
            optimiser.zero_grad(set_to_none=True)
            if writer is not None and rank == 0:
                writer.add_scalar(
                    "Loss/train",
                    step_loss / accum,
                    step * len(data_loader) + i,
                )
            step_loss = 0.0

        epoch_losses.append(loss.item())
        if rank == 0:
            iterator.set_postfix_str(s=f"Loss: {loss.item():.4f}")

    mean_loss = sum(epoch_losses) / len(epoch_losses)
    mean_loss = reduce_mean(mean_loss, device, world_size)

    if rank == 0:
        iterator.set_postfix_str(s=f"Loss: {mean_loss:.4f}")
        iterator.close()

    return mean_loss


# -----------------------------------------------------------------------------
# Author-style EDM/Heun validation sampling (unchanged algorithmically).

@torch.no_grad()
def sample_model(
    model,
    dataloader,
    num_steps=40,
    sigma_min=0.002,
    sigma_max=80,
    rho=7,
    S_churn=40,
    S_min=0,
    S_max=float("inf"),
    S_noise=1,
    device="cuda",
):
    net = model.module if isinstance(model, DDP) else model
    net.eval()

    batch = next(iter(dataloader))
    images_input = batch["inputs"].to(device)
    coarse, fine = batch["coarse"], batch["fine"]

    condition_params = torch.stack(
        (batch["year"].to(device), batch["doy"].to(device)),
        dim=1,
    )

    sigma_min = max(sigma_min, net.sigma_min)
    sigma_max = min(sigma_max, net.sigma_max)

    init_noise = torch.randn(
        (
            images_input.shape[0],
            dataloader.dataset.target_channels,
            images_input.shape[2],
            images_input.shape[3],
        ),
        dtype=torch.float64,
        device=device,
    )

    step_indices = torch.arange(
        num_steps,
        dtype=torch.float64,
        device=init_noise.device,
    )
    t_steps = (
        sigma_max ** (1 / rho)
        + step_indices / (num_steps - 1)
        * (sigma_min ** (1 / rho) - sigma_max ** (1 / rho))
    ) ** rho
    t_steps = torch.cat(
        [net.round_sigma(t_steps), torch.zeros_like(t_steps[:1])]
    )

    x_next = init_noise.to(torch.float64) * t_steps[0]

    for i, (t_cur, t_next) in enumerate(zip(t_steps[:-1], t_steps[1:])):
        x_cur = x_next
        gamma = (
            min(S_churn / num_steps, np.sqrt(2) - 1)
            if S_min <= t_cur <= S_max
            else 0
        )
        t_hat = net.round_sigma(t_cur + gamma * t_cur)
        x_hat = (
            x_cur
            + (t_hat ** 2 - t_cur ** 2).sqrt()
            * S_noise
            * torch.randn_like(x_cur)
        )

        denoised = net(
            x_hat,
            t_hat,
            images_input,
            condition_params,
        ).to(torch.float64)
        d_cur = (x_hat - denoised) / t_hat
        x_next = x_hat + (t_next - t_hat) * d_cur

        if i < num_steps - 1:
            denoised = net(
                x_next,
                t_next,
                images_input,
                condition_params,
            ).to(torch.float64)
            d_prime = (x_next - denoised) / t_next
            x_next = x_hat + (t_next - t_hat) * (
                0.5 * d_cur + 0.5 * d_prime
            )

    predicted = dataloader.dataset.residual_to_fine_image(
        x_next.detach().cpu(), coarse
    )

    fig, ax = dataloader.dataset.plot_batch(coarse, fine, predicted)
    plt.subplots_adjust(wspace=0, hspace=0)
    base_error = torch.mean(torch.abs(fine - coarse))
    pred_error = torch.mean(torch.abs(fine - predicted))

    return (fig, ax), (base_error.item(), pred_error.item())


# -----------------------------------------------------------------------------
# CLI.

def parse_int_list(text):
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def build_argparser():
    parser = argparse.ArgumentParser(
        description=(
            "Author-style Taiwan precipitation EDM training with bilinear tp, "
            "DDP, and optional self-attention ablation."
        )
    )

    parser.add_argument("--data-dir", required=True)
    parser.add_argument(
        "--resolution",
        default="8km",
        choices=["1km", "5km", "8km"],
    )
    parser.add_argument("--train-start", default="19600101")
    parser.add_argument("--train-end", default="20141125")
    parser.add_argument("--val-start", default="20141126")
    parser.add_argument("--val-end", default="20171213")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--accum", type=int, default=8)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--sample-steps", type=int, default=40)
    parser.add_argument("--stats-samples", type=int, default=2048)
    parser.add_argument("--output-dir", required=True)

    # Explicit architecture arguments. Defaults match IDW_loss/dev/Network.py.
    # Your existing experiment can explicitly pass --model-channels 64.
    parser.add_argument("--model-channels", type=int, default=128)
    parser.add_argument("--channel-mult", default="1,2,3,4")
    parser.add_argument("--num-blocks", type=int, default=2)
    parser.add_argument("--attn-resolutions", default="32,16,8")
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--use-fp16", action="store_true")
    parser.add_argument("--sigma-data", type=float, default=1.0)

    # The only intended experimental variable for the attention ablation.
    attention_group = parser.add_mutually_exclusive_group()
    attention_group.add_argument(
        "--use-attention",
        dest="use_attention",
        action="store_true",
        help="Train CNN U-Net + self-attention.",
    )
    attention_group.add_argument(
        "--no-attention",
        dest="use_attention",
        action="store_false",
        help="Train CNN-only U-Net; attention parameters are not created.",
    )
    parser.set_defaults(use_attention=True)

    return parser


def main():
    args = build_argparser().parse_args()
    rank, world_size, local_rank, device = setup_distributed()

    torch.manual_seed(42 + rank)
    np.random.seed(42 + rank)

    output_dir = Path(args.output_dir)
    result_dir = output_dir / "results"
    model_dir = output_dir / "Model"
    run_dir = output_dir / "runs"
    stats_path = output_dir / f"stats_{args.resolution}.json"

    channel_mult = parse_int_list(args.channel_mult)
    attn_resolutions = parse_int_list(args.attn_resolutions)

    if rank == 0:
        result_dir.mkdir(parents=True, exist_ok=True)
        model_dir.mkdir(parents=True, exist_ok=True)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save the exact architecture/training switches used for reproducibility.
        config = vars(args).copy()
        config["channel_mult"] = channel_mult
        config["attn_resolutions"] = attn_resolutions
        config["world_size"] = world_size
        config["effective_batch_nominal"] = (
            args.batch_size * world_size * args.accum
        )
        (output_dir / "train_config.json").write_text(
            json.dumps(config, indent=2),
            encoding="utf-8",
        )

        print(
            "[Architecture] "
            f"use_attention={args.use_attention} "
            f"model_channels={args.model_channels} "
            f"channel_mult={channel_mult} "
            f"num_blocks={args.num_blocks} "
            f"attn_resolutions={attn_resolutions} "
            f"dropout={args.dropout}"
        )
        print(
            "[DDP] "
            f"world_size={world_size} batch_per_gpu={args.batch_size} "
            f"accum={args.accum} "
            f"nominal_effective_batch={args.batch_size * world_size * args.accum}"
        )

        if not stats_path.exists():
            stats_dataset = TaiwanERAPrecipDataset(
                data_dir=args.data_dir,
                resolution=args.resolution,
                start_date=args.train_start,
                end_date=args.train_end,
                condition_vars=["q700", "t2m", "u", "v", "msl", "tp"],
                use_mask=True,
                target_transform="log1p",
                stats=None,
            )
            stats = compute_stats(
                stats_dataset,
                max_samples=args.stats_samples,
            )
            save_stats(stats, stats_path)
            stats_dataset.close()

    dist.barrier(device_ids=[local_rank])
    stats = load_stats(stats_path)

    dataset_train = TaiwanERAPrecipDataset(
        data_dir=args.data_dir,
        resolution=args.resolution,
        start_date=args.train_start,
        end_date=args.train_end,
        condition_vars=["q700", "t2m", "u", "v", "msl", "tp"],
        use_mask=True,
        target_transform="log1p",
        stats=stats,
    )

    dataset_val = TaiwanERAPrecipDataset(
        data_dir=args.data_dir,
        resolution=args.resolution,
        start_date=args.val_start,
        end_date=args.val_end,
        condition_vars=["q700", "t2m", "u", "v", "msl", "tp"],
        use_mask=True,
        target_transform="log1p",
        stats=stats,
    )

    train_sampler = DistributedSampler(
        dataset_train,
        num_replicas=world_size,
        rank=rank,
        shuffle=True,
    )

    dataloader_train = DataLoader(
        dataset_train,
        batch_size=args.batch_size,
        sampler=train_sampler,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    dataloader_val = None
    if rank == 0:
        dataloader_val = DataLoader(
            dataset_val,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=args.num_workers,
        )

    model_in_channels = (
        dataset_train.num_input_channels + dataset_train.target_channels
    )
    model_out_channels = dataset_train.target_channels

    # Modified: architecture is explicit and use_attention is passed to UNet.
    network = networkold.EDMPrecond(
        dataset_train.img_resolution,
        model_in_channels,
        model_out_channels,
        label_dim=2,
        use_fp16=args.use_fp16,
        sigma_data=args.sigma_data,
        model_channels=args.model_channels,
        channel_mult=channel_mult,
        num_blocks=args.num_blocks,
        attn_resolutions=attn_resolutions,
        dropout=args.dropout,
        use_attention=args.use_attention,
    )
    network.to(device)

    network = DDP(
        network,
        device_ids=[local_rank],
        output_device=local_rank,
        find_unused_parameters=False,
    )

    scaler = torch.cuda.amp.GradScaler()
    optimiser = torch.optim.AdamW(network.parameters(), lr=args.lr)
    writer = SummaryWriter(str(run_dir)) if rank == 0 else None
    loss_fn = EDMLoss(sigma_data=args.sigma_data)

    losses = []
    for step in range(0, args.epochs):
        train_sampler.set_epoch(step)

        epoch_loss = training_step(
            network,
            loss_fn,
            optimiser,
            dataloader_train,
            scaler,
            step,
            world_size,
            args.accum,
            writer,
            device,
            rank,
        )

        if rank == 0:
            losses.append(epoch_loss)

            if step % args.sample_every == 0:
                (fig, ax), (base_error, pred_error) = sample_model(
                    network,
                    dataloader_val,
                    num_steps=args.sample_steps,
                    device=device,
                )
                fig.savefig(result_dir / f"{step}.png", dpi=300)
                plt.close(fig)

                writer.add_scalar("Error/base", base_error, step)
                writer.add_scalar("Error/pred", pred_error, step)

            if losses[-1] == min(losses):
                torch.save(
                    network.module.state_dict(),
                    model_dir / f"{step}.pt",
                )

        dist.barrier(device_ids=[local_rank])

    dataset_train.close()
    dataset_val.close()
    if writer is not None:
        writer.close()

    cleanup_distributed()


if __name__ == "__main__":
    main()
