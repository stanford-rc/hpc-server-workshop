#!/bin/bash
#SBATCH --job-name=data-server
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --output=logs/server_%j.out

# The server writes its address here; the client job reads it.
# $SCRATCH is accessible from all Sherlock nodes.
export SERVER_ADDR_FILE="$SCRATCH/hpc_workshop_server.txt"

module load python/3.12.1
source venv/bin/activate

python server.py
