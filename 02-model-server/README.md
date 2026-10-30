# Tier 2: A model server

Tier 1's server held a table. This one holds a **language model**, the kind of
program behind chatbots. Models are a good reason to run a server: loading one
takes time and GPU memory, so you load it once and send it many prompts.

There are two ways to do it, and you'll try both:

| | **A. Ollama** | **B. Your own server (transformers)** |
|---|---|---|
| What it is | A ready-made model server, installed on Sherlock as a module | A small server you write, using the Hugging Face `transformers` library |
| You write | nothing | `server.py` (provided) |
| Models | Ollama's collection; Sherlock keeps a library of hundreds on Oak | almost any model on the Hugging Face Hub |
| Who can reach it | only programs on the same machine | any machine on Sherlock, with your token |

Ollama is the quick start. Your own server is what you'd use for a specific
model, for example one trained for your field.

## Files

| File | What it is |
|------|------------|
| `submit_ollama.sh` | A: starts Ollama and writes its address |
| `ollama_client.py` | A: sends a few questions to Ollama |
| `server.py` | B: loads a model and answers prompts at `/generate` |
| `submit_server.sh` | B: starts `server.py` |
| `client.py`, `submit_client.sh` | B: sends a few prompts to `server.py` |

## 1. A session with a GPU

Start from a login node, with Tier 1 closed (its step 6). Tier 2 needs a GPU,
so it's a **new session**, on a different machine, and the second terminal will
`ssh` to that new machine. Your token file and the workshop files carry over.

Language models run much faster on a **GPU**. Sherlock's `dev` machines have
GPU **slices**: one physical GPU split into several smaller ones, each with
6 GB of its own memory. A slice is plenty for the small models used here, and
usually starts right away:

```bash
sh_dev -g 1 -m 8000
```

`-g 1` asks for one GPU slice and `-m 8000` for 8,000 MB (about 8 GB) of memory,
since the model and its libraries need more than the default 4 GB.

## 2. A: Ollama

In the session:

```bash
ml purge
ml ollama
cd ~/hpc-server-workshop/02-model-server
bash submit_ollama.sh
```

`ml purge` clears any modules this terminal already had, and `ml ollama` makes
Ollama available.
The script starts Ollama on a free port, gets the model and writes Ollama's
address to `$SCRATCH/hpc_workshop_ollama.txt`. The model is `gemma3:4b`, a
4-billion-parameter model from Google that fits easily on a slice (about
3 GB). You don't download it from the internet: Sherlock keeps a library of
Ollama models on Oak, and the first time you use one it's copied into your
scratch space (the script prints "found in on-prem cache"). Leave it running.

Ollama doesn't have a password or token, so it only accepts connections from
the machine it runs on. To talk to it, open a **second terminal**, log in to
the session's machine, putting its name (from your session's prompt) in place
of `<machine>`:

```bash
ssh <machine>
```

Then run the client:

```bash
cd ~/hpc-server-workshop/02-model-server
ml python/3.12.1
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate
python3 ollama_client.py
```

The second and third commands make the workshop's Python packages available,
the same two lines every script in this workshop starts with. (If you see a
note that `gcc` was reloaded with a version change, that's harmless.) In
testing the two answers took about 20 seconds.

**Choosing a model.** Sherlock has hundreds of Ollama models. To see them all,
list the library:

```bash
ls /oak/stanford/datasets/common/ollama/manifests/registry.ollama.ai/library
```

The folder names are the model names, and the files inside each are its sizes
(for example `gemma3` has `1b`, `4b`, `12b`, `27b`). On a GPU slice, stay at
about 4b or below. To use one, stop Ollama with Ctrl-C in the first terminal,
start it with that model, and run the client with the same name:

```bash
MODEL=<name>:<size> bash submit_ollama.sh
```

```bash
MODEL=<name>:<size> python3 ollama_client.py
```

Stop Ollama with **Ctrl-C** before part B, so the two don't compete for the
slice's memory.

## 3. B: your own model server

In the first terminal (the session):

```bash
bash submit_server.sh
```

This starts `server.py`, which loads `Qwen2.5-1.5B-Instruct` onto the GPU: a
small model from Alibaba, trained to answer questions, with a license that
lets anyone use it. Hugging Face models aren't in Sherlock's Ollama library, so
for the workshop it's already downloaded to a shared folder, and nothing has
to be fetched. In testing it was ready in 20 to 60 seconds. When it prints
`Model ready on <machine>:<port>`, run the client in the second terminal:

```bash
bash submit_client.sh
```

Three questions come back with one-sentence answers, in a few seconds.

Like Tier 1, this server can be reached from any machine on Sherlock, so it
uses your token. Here is the same request by hand:

```bash
curl -s -H "x-token: $(cat ~/.hpc_workshop/token)" -H "Content-Type: application/json" -d '{"prompt": "In one sentence, what is a GPU?", "max_new_tokens": 60}' "http://$(cat $SCRATCH/hpc_workshop_model.txt)/generate"
```

Stop it with Ctrl-C, and `exit` the session when you're done.

### Choosing a model

Set `MODEL_NAME` in `submit_server.sh` to another chat model on the Hugging
Face Hub (look for "Instruct" or "chat" in the name). A few things to know:

- **Size.** A GPU slice has 6 GB of memory. `server.py` loads models in half
  precision, about 2 GB per billion parameters, so stay at about 2 billion
  parameters or below on a slice. `server.py` uses one GPU, so bigger models need a full GPU
  in a batch job (see "Running it for real") and possibly changes to `server.py`.
- **Downloads.** Outside the workshop, remove the `HF_HUB_CACHE` and
  `HF_HUB_OFFLINE` lines from `submit_server.sh`. The model then downloads once
  into `$SCRATCH/hf_cache` and loads from there after that. (Files in `$SCRATCH`
  are deleted after 90 days unused.)
- **Gated models.** Some models, such as Meta's Llama, need you to accept a
  license on the Hugging Face website and log in with a Hugging Face token
  before they'll download.

**Models for your field.** The Hub has many models already trained for a
subject or a task: scientific text (`allenai/scibert_scivocab_uncased`),
biomedical papers (`dmis-lab/biobert-base-cased-v1.2`), protein sequences
(`facebook/esm2_t33_650M_UR50D`). Ollama doesn't carry these, which is the
main reason to write your own server. Many of them don't generate text; they
classify it, fill in missing words or turn it into numbers. For those, change
`pipeline("text-generation", ...)` in `server.py` to the task you need
(`fill-mask`, `feature-extraction`, `text-classification`,
`token-classification`), and change `/generate` to pass in the plain text
(not a chat message) and return what that task produces. The session,
address file and token don't change.

## Running it for real

For a working session longer than `sh_dev` allows, or a model too big for a
slice, submit the server as a batch job. It stops when its `--time` runs out.
`submit_server.sh` and `submit_ollama.sh` already ask for a full GPU on
Sherlock's `gpu` machines in their `#SBATCH` lines:

```bash
mkdir -p logs
sbatch submit_server.sh
```

GPU slices are only available in `sh_dev` sessions, so a batch job gets a whole
GPU and may wait in the queue first.

## Your own Python packages

Part B's packages (`torch` especially) take about 5 GB. To make your own set
for your projects, see "Making your own environment" in the
[top-level README](../README.md#making-your-own-environment), and keep it in
`$GROUP_HOME`, not `$HOME`.
