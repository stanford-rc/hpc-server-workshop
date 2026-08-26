#!/bin/bash
#SBATCH --job-name=model-server
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gpus=1
#SBATCH --output=logs/server_%j.out

# For a larger model, increase mem and cpus. For multi-GPU:
#   #SBATCH --gpus=2
#   Set tensor_parallel_size in the generation call accordingly.

export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"

# Cache HF model weights in $SCRATCH so they persist across jobs.
# First run will download; subsequent runs load from cache.
export HF_HOME="$SCRATCH/hf_cache"

# Swap MODEL_NAME for a larger model when you have GPU resources.
export MODEL_NAME="distilgpt2"

module load python/3.12.1
source venv/bin/activate

python server.py
