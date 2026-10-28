# Tier 2: A model server

Tier 1's server held a table. This one holds a **language model**, the kind of
program behind chatbots. Models are a good reason to run a server: loading one
takes time and GPU memory, so you load it once and send it many prompts.

There are two ways to do it, and you'll try both:

| | **A. Ollama** | **B. Your own server (transformers)** |
|---|---|---|
| What it is | A ready-made model server, installed on Sherlock as a module | A small server you write, using the Hugging Face `transformers` library |
| You write | nothing | `server.py` (provided) |
| Models | Ollama's collection; Sherlock keeps copies of many | almost any model on the Hugging Face Hub |
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
ml ollama
cd ~/hpc-server-workshop/02-model-server
bash submit_ollama.sh
```

`ml` is short for `module load`: it makes Ollama available in this terminal.
The script starts Ollama on a free port, fetches the model (`llama3.2:1b`, a
small one) and writes Ollama's address to `$SCRATCH/hpc_workshop_ollama.txt`.
In testing it was ready in about 40 seconds. Leave it running.

Ollama doesn't have a password or token, so it only accepts connections from
the machine it runs on. To talk to it, open a **second terminal**, log in to
the session's machine (the name in your session's prompt), and run the client:

```bash
ssh <machine>
cd ~/hpc-server-workshop/02-model-server
ml python/3.12.1
source /home/groups/sh_support/bcritt/server_workshop/venv/bin/activate
python ollama_client.py
```

The second and third commands make the workshop's Python packages available,
the same two lines every script in this workshop starts with. After about 15
seconds you get two answers. Read them closely: a model this small often
sounds sure of itself and is wrong. In testing it explained "SLURM" with a
made-up name. That's normal for small models, and a good reason to check what
a model tells you.

To try another model, stop Ollama with Ctrl-C in the first terminal and start
it again with `MODEL=<name> bash submit_ollama.sh`, then run the client with the
same `MODEL=<name>` in front. Model names are listed at ollama.com/library; keep
to small ones on a GPU slice. If Sherlock already has a copy, fetching it is
quick.

Stop Ollama with **Ctrl-C** before part B, so the two don't compete for the
slice's memory.

## 3. B: your own model server

In the first terminal (the session):

```bash
bash submit_server.sh
```

This starts `server.py`, which loads `distilgpt2`, a tiny text model, onto the
GPU. For the workshop the model is already downloaded to a shared folder, so
nothing has to be fetched. Loading takes about a minute. When it prints
`Model ready on <machine>:<port>`, run the client in the second terminal:

```bash
bash submit_client.sh
```

Each prompt comes back with a continuation. `distilgpt2` is old and tiny, so
the text is mostly nonsense. What matters here is the steps, not the model.

Like Tier 1, this server can be reached from any machine on Sherlock, so it
uses your token. Here is the same request by hand:

```bash
curl -s -H "x-token: $(cat ~/.hpc_workshop/token)" -H "Content-Type: application/json" -d '{"prompt": "The cluster is", "max_new_tokens": 30}' "http://$(cat $SCRATCH/hpc_workshop_model.txt)/generate"
```

Stop it with Ctrl-C, and `exit` the session when you're done.

### Choosing a model

`distilgpt2` is only there to test the steps. For real work, set `MODEL_NAME`
in `submit_server.sh` to any text-generation model on the Hugging Face Hub. A
few things to know:

- **Size.** A GPU slice has 6 GB of memory, enough for models up to about a
  billion parameters. `server.py` uses one GPU, so bigger models need a full GPU
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
`token-classification`) and adjust what `/generate` returns. The session,
address file and token don't change.

## Running it for real

For a model server that runs longer than a session, submit it as a batch job.
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
