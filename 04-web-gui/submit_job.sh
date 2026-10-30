#!/bin/bash
# Brad Rittenhouse, Stanford Research Computing (bcritt@stanford.edu)
#SBATCH --job-name=web-gui-predict    # name shown in the queue
#SBATCH --time=00:30:00               # stop the job after this long (hours:minutes:seconds)
#SBATCH --ntasks=1                    # run one copy of the program
#SBATCH --cpus-per-task=2             # CPU cores for it
#SBATCH --mem=4G                      # memory (RAM) for the job
#SBATCH --output=logs/predict_%j.out  # save what the job prints here (%j becomes the job ID)

# The compute step: read an uploaded input, send it to the Tier 2 model
# server, and write the results where the web page can offer them.
#
# Run it after uploading an input file through the web page:
#   bash submit_job.sh                 # newest .txt in inputs/
#   bash submit_job.sh prompts.txt     # a specific file

export RESULTS_DIR="$PWD/results"
export INPUTS_DIR="$PWD/inputs"

# Which Tier 2 model server to use, and where it wrote its address.
#
# Ollama (the workshop path):
export MODEL_API="openai"
export MODEL_ADDR_FILE="$SCRATCH/hpc_workshop_ollama.txt"
export MODEL="${MODEL:-gemma3:4b}"
#
# The transformers server instead:
# export MODEL_API="generate"
# export MODEL_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"
#
# Ollama only accepts connections from its own machine, so run this script in
# a terminal on that machine: ssh to it from a login node first.

module load python/3.12.1    # make Sherlock's Python 3.12 available
# The workshop's shared Python packages. For your own project, make your own
# environment (see the README) and activate that instead.
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate

python predict.py "$@"
