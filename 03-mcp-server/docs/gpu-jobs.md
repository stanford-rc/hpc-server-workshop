# Requesting GPUs

GPU nodes live in the `gpu` partition. Request one with `--gpus`:

```bash
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=4:00:00
```

## Selecting GPU memory

Different nodes have different cards. Constrain by memory rather than by
model name so your job stays schedulable:

```bash
#SBATCH --constraint="GPU_MEM:32GB|GPU_MEM:48GB|GPU_MEM:80GB"
```

## Quick interactive GPU

For testing, `sh_dev -g 1` gets a lightweight GPU allocation immediately
without waiting in the main queue.

## Common problems

**CUDA out of memory** — request a card with more memory via `--constraint`,
or reduce batch size. Check what you actually got with `nvidia-smi`.

**Job pending forever** — you may have over-constrained. Ask for a range of
GPU memory sizes instead of one specific card.
