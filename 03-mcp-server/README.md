# Tier 3 — MCP Server

**Model Context Protocol (MCP)** is a standard interface for giving AI
assistants structured access to tools and data. Where tiers 1–2 expose HTTP
endpoints that you call explicitly, an MCP server lets the assistant *decide*
which tools to call and in what order, based on a natural-language question.

You run the tools on Sherlock. Claude on your laptop runs the model. Ask
"how do I stop hitting my quota?" and Claude picks `search_docs`, then
`read_doc`, and answers from what it finds.

## How this differs from tiers 1–2

| | Tier 1–2 (HTTP) | Tier 3 (MCP) |
|---|---|---|
| Client | Python script you write | Claude Desktop or Claude Code |
| Invocation | You call the endpoint | The model decides what to call |
| Interface | URLs and JSON you designed | Tools it discovers at connect time |
| Use case | Batch jobs, notebooks | Conversational, exploratory |

## What runs where

```
  your laptop                  SSH tunnel          Sherlock compute node
 ┌──────────────────┐                             ┌────────────────────┐
 │ Claude Desktop   │                             │  mcp_server.py     │
 │ or Claude Code   │ ──── tools/list ──────────▶ │   list_docs        │
 │                  │ ──── tools/call ──────────▶ │   read_doc         │
 │ (model runs      │ ◀─── results ────────────── │   search_docs      │
 │  Anthropic-side) │                             │      │             │
 └──────────────────┘                             │   docs/            │
                                                  └────────────────────┘
                                                       no GPU needed
```

**No GPU, and no model on the cluster.** This process reads files and matches
strings. That's the point of MCP: the tools and the model are separate
services, so the expensive half is somebody else's problem. The tradeoff is
that your questions and the retrieved text go to Anthropic — if that's not
acceptable, see [Keeping it all on Sherlock](#keeping-it-all-on-sherlock).

## Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server over Streamable HTTP — `list_docs`, `read_doc`, `search_docs` |
| `docs/` | The documentation the tools expose (three sample files) |
| `submit_server.sh` | sbatch script (no GPU, 4h walltime) |
| `requirements.txt` | `mcp>=2.0`, `uvicorn` |

## Setup

```bash
module load python/3.12.1
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# SLURM needs this to exist before you submit — --output is resolved at
# submit time, and logs/ is gitignored so a fresh clone won't have it.
mkdir -p logs
```

> MCP 2.x renamed `FastMCP` to `MCPServer`. `requirements.txt` pins `mcp>=2.0`
> to match this code. The production server elsewhere in this repo was written
> against 1.x and uses the old name.

## Run

```bash
# 1. Start the server on a compute node
sbatch submit_server.sh
tail -f logs/server_<jobid>.out     # prints the exact commands to run next

# 2. Forward a local port — same pattern as Tier 4
ADDR=$(cat $SCRATCH/hpc_workshop_mcp.txt)
ssh -NfL 8080:localhost:${ADDR#*:} ${ADDR%:*}
```

Streamable HTTP is ordinary HTTP, so the tunnel is identical to
[Tier 4's](../04-web-gui/README.md#2-you-forward-a-local-port-to-it) —
including the requirement that the bind address match the tunnel form. The MCP
endpoint is at **`/mcp`**, so through the tunnel it's
`http://localhost:8080/mcp`.

### Connect Claude Code

```bash
claude mcp add --transport http workshop-docs http://localhost:8080/mcp
claude mcp list          # confirm it registered
```

### Connect Claude Desktop

Claude Desktop can't take a remote URL directly — `"type": "sse"` is not
valid in `claude_desktop_config.json`, which is why everything goes through the
`mcp-remote` shim. Add to
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "workshop-docs": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8080/mcp"]
    }
  }
}
```

Restart Claude Desktop. Requires Node.js for `npx`.

### Try it

Ask a question that needs the tools rather than naming one:

- "What storage should I use for job output on Sherlock, and why?"
- "My job died with CUDA out of memory. What do the docs suggest?"
- "How do I load a specific version of Python in a batch script?"

## Troubleshooting

| Symptom | Cause |
|---|---|
| `406 Not Acceptable` | Client didn't send `Accept: application/json, text/event-stream`. Real clients do; hand-rolled `curl` often doesn't |
| `421 Invalid Host header` | You forwarded to a local port the server doesn't allow. Set `ALLOWED_HOSTS="localhost:<your port>"` in `submit_server.sh` |
| `Connection refused` | Tunnel points at the wrong place — see [Tier 4](../04-web-gui/README.md#3-you-open-httplocalhost8080) |
| Tools don't appear | Restart the client after editing config; check `claude mcp list` |

DNS-rebinding protection is on by default and validates the `Host` header.
Through a tunnel the client sends `localhost:8080`, which isn't the server's
own hostname — so allowed hosts must be set explicitly. `mcp_server.py` allows
the common local ports; anything else needs `ALLOWED_HOSTS`.

## Keeping it all on Sherlock

The default path sends your prompts and the retrieved document text to
Anthropic. To keep everything inside Stanford, run the model on Sherlock too —
`ml ollama` on a GPU node, exactly the service pattern from Tier 2, with its
endpoint in `~/.ollama_server`. Then either:

- **Stay in the terminal.** Point a CLI agent at the local model. Several
  Sherlock modules support this — OpenCode, Crush, and `pi` all take an
  OpenAI-compatible `base_url`, and several also speak MCP, so they can use
  this server's tools with a local model.
- **Drive it from your laptop.** Forward two ports — Ollama's and this
  server's — so the model and the tools both stay on the cluster while you
  work in a local editor.

The honest caveat: small local models are noticeably worse at multi-step tool
calling than the hosted ones. They pick the wrong tool, or loop. Ollama also
caps the context window at 4k on GPUs under 24 GB regardless of what the model
supports, and agents need far more — so you must raise `num_ctx` via a
Modelfile before an agent works at all.

See the Sherlock docs for the details, which are more current than anything
pinned here: [Ollama][ollama] and [AI coding agents][agents].

## Adapting this

`search_docs` is a case-insensitive substring scan — deliberately the dumbest
thing that works. Swapping that one function for real retrieval (BM25, vector
search) is how this becomes useful on a real corpus. The tool interface stays
the same, so the client never notices.

Point `DOCS_DIR` at your own directory of markdown and the tools work
unchanged.

[ollama]: https://www.sherlock.stanford.edu/docs/software/using/ollama/
[agents]: https://www.sherlock.stanford.edu/docs/software/ai/coding-agents/
