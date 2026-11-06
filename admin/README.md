# Running the workshop: notes for instructors

Learners don't need anything in this folder. It's for whoever sets up and
teaches the workshop.

## What's prepared on Sherlock

Everything lives in `/home/groups/sh_support/bcritt/server_workshop/`, which
every Sherlock user can read but not change:

| Path | What it is |
|---|---|
| `venv/` | The shared Python environment every tier's scripts `source` (about 5 GB, mostly `torch`) |
| `build-env.sh`, `requirements-all.txt` | How `venv/` was built (copies in this folder) |
| `versions.txt` | The exact package versions in `venv/` (copy in this folder) |
| `hf_cache/hub/` | Pre-downloaded Hugging Face models for Tier 2 part B |

The Ollama models (Tiers 2 and 4) aren't here. They come from Sherlock's own
library on Oak (`/oak/stanford/datasets/common/ollama`) through the `ollama`
module, so there's nothing to prepare for them.

## Rebuilding the shared environment

Do this if a module version in the scripts changes (`python/3.12.1`), or to pick
up newer packages. Copy `build-env.sh` and `requirements-all.txt` from this
folder into the shared folder, then, from a login node:

```bash
sh_dev -c 4 -m 16000 -t 1:00:00
bash /home/groups/sh_support/bcritt/server_workshop/build-env.sh
```

Then copy the new `versions.txt` back into this
folder and commit it, and rerun every tier on `dev` (see "Before teaching").

Why it's built this way:

- **`uv pip install --no-build`.** Sherlock's operating system (CentOS 7,
  glibc 2.17) is too old for the newest builds of numpy and torch. Plain pip
  falls back to compiling numpy from source and fails after about seven
  minutes. `--no-build` makes uv pick the newest versions that do have
  ready-made builds for Sherlock (numpy 2.2.6 and torch 2.6.0 at last build).
- **Built from the `python/3.12.1` module**, so the environment works after
  learners run `ml python/3.12.1`, as every script does.
- **In `$GROUP_HOME`, not `$SCRATCH`**: scratch is purged after 90 days
  without changes.

## Hugging Face models for Tier 2

`02-model-server/submit_server.sh` points `HF_HUB_CACHE` at `hf_cache/hub/`
and sets `HF_HUB_OFFLINE=1`, so learners load the model from the shared copy
and nothing downloads on the day. Set both variables, because `HF_HUB_CACHE`
wins over `HF_HOME`, and a learner may have it set in their login files.

The cache holds `Qwen/Qwen2.5-1.5B-Instruct` (the Tier 2 default) and
`distilgpt2` (no longer used by any tier). To add a model, in an `sh_dev`
session:

```bash
ml python/3.12.1
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('<model name>', cache_dir='/home/groups/sh_support/bcritt/server_workshop/hf_cache/hub')"
```

Then check that every user can read it (`ls -l`; files should be `r--` for
"other").

## Before teaching

- **Run every tier on `dev`, exactly as the READMEs say**, from a fresh login,
  as a learner would. `dev` refuses `sbatch`, so learners run the scripts with
  `bash submit_*.sh` inside `sh_dev`; the `#SBATCH` lines are only for running
  them as batch jobs.
- **`dev` limits per person**: 2 sessions at once, 4 CPU cores, 2 GPUs and
  16 GB of memory in total, 2 hours at most (1 hour by default). Tier 2 and
  Tier 4 each use one session with a GPU slice (`sh_dev -g 1 -m 8000`).
- **GPU slices** (A30, 6 GB each) exist only on `dev`'s two GPU machines.
  With a full room, check that there are enough free: `sinfo -p dev`.
- **Check the `sbatch` scripts still submit**, without running them:
  `sbatch --test-only submit_server.sh` in each tier.
- **Learners whose SSH settings use `ControlMaster`** (Sherlock's docs suggest
  it) can find a tunnel's laptop port still held after Ctrl-C. Every tunnel
  command uses `ssh -S none` to avoid that; if someone types it without, `ssh
  -O exit login.sherlock.stanford.edu` frees the port.

## Slides

`HPC-Server-Workshop.pptx` is generated; see [`slides-src/README.md`](../slides-src/README.md).
The workshop is taught from the READMEs, so the slides are a summary only.
