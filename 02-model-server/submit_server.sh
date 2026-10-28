#!/bin/bash
#SBATCH --job-name=model-server      # name shown in the queue
#SBATCH --time=1:00:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                   # run one copy of the program
#SBATCH --cpus-per-task=4            # CPU cores for it
#SBATCH --mem=16G                    # memory (RAM) for the job
#SBATCH --gpus=1                     # number of GPUs
#SBATCH --partition=gpu              # the machines that have GPUs
#SBATCH --output=logs/server_%j.out  # save what the job prints here (%j becomes the job ID)

# server.py puts the model on one GPU, so asking for more GPUs here doesn't
# help. A model too big for one GPU needs changes to server.py first.

# Where the server writes its address, so other jobs can find it.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"

# Where Hugging Face keeps its files. $SCRATCH is your fast scratch space;
# files there are deleted after 90 days unused.
export HF_HOME="$SCRATCH/hf_cache"

# For the workshop, the model is already downloaded to a shared, read-only
# folder, so nobody has to download it. HF_HUB_OFFLINE=1 means "use what's
# there, don't try to download or check for updates".
# For your own work, delete these two lines; the model then downloads once
# into $HF_HOME and loads from there after that.
export HF_HUB_CACHE="/home/groups/sh_support/bcritt/server_workshop/hf_cache/hub"
export HF_HUB_OFFLINE=1

# Which model to serve. distilgpt2 is tiny, for trying out the steps.
export MODEL_NAME="distilgpt2"

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

python server.py
