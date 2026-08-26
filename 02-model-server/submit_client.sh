#!/bin/bash
#SBATCH --job-name=model-client
#SBATCH --time=0:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --output=logs/client_%j.out

# Must match the path in submit_server.sh.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_model.txt"

module load python/3.12.1
source venv/bin/activate

python client.py
