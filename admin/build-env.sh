#!/bin/bash
# Builds the shared Python environment for the HPC Server Workshop.
# Run it inside an interactive session, not on a login node:
#   sh_dev -c 4 -m 16000 -t 1:00:00
#   bash /home/groups/sh_support/bcritt/server_workshop/build-env.sh
set -euo pipefail

HERE=/home/groups/sh_support/bcritt/server_workshop
ENV="$HERE/venv"

ml python/3.12.1 uv/0.10.8

# Build from Sherlock's Python module, so learners load the same module first.
uv venv --python "$(command -v python3)" "$ENV"

# --no-build: only use ready-made packages that work on Sherlock (CentOS 7).
# Without it, pip and uv try to compile numpy from source here, which fails.
# --no-cache: don't fill ~/.cache with downloads.
uv pip install --python "$ENV/bin/python" --no-build --no-cache -r "$HERE/requirements-all.txt"

uv pip list --python "$ENV/bin/python" > "$HERE/versions.txt"
echo "Built $ENV"; du -sh "$ENV"
