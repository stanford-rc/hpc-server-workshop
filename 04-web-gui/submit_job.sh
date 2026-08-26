#!/bin/bash
#SBATCH --job-name=web-gui-predict
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=logs/predict_%j.out

# The compute step: read an uploaded input, call the Tier 2 model server,
# write outputs where the web server can serve them.
#
# Submit this after uploading an input file through the web page:
#   sbatch submit_job.sh                 # newest .txt in inputs/
#   sbatch submit_job.sh prompts.txt     # a specific file

export RESULTS_DIR="$PWD/results"
export INPUTS_DIR="$PWD/inputs"

# Which Tier 2 backend to call, and where it wrote its address.
#
# Ollama (the workshop path — no torch install, no queue wait on a MIG slice):
export MODEL_API="openai"
export MODEL_ADDR_FILE="$SCRATCH/hpc_workshop_ollama.txt"
export MODEL="${MODEL:-llama3.2:1b}"
#
# Transformers instead (a specific pre-tuned model from the Hub):
# export MODEL_API="generate"
# export MODEL_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"
#
# NOTE: with Ollama bound to loopback (the default), this job can only reach it
# if it lands on the same node. Either run predict.py inside the Ollama
# allocation, or start Ollama with OLLAMA_BIND=0.0.0.0 — see the security note
# in ../02-model-server/submit_ollama.sh.

module load python/3.12.1
source venv/bin/activate

python predict.py "$@"
