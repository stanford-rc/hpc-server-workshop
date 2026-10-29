# Tier 3: An MCP server for Claude

In Tiers 1 and 2 you wrote the questions: the client asked for `/stats` or sent
a prompt. Here an AI assistant decides what to ask.

**MCP** (Model Context Protocol) is a standard way to give an AI assistant like
Claude a set of **tools** it can use. This server offers three tools for a
folder of Sherlock documentation (`docs/`, three short sample files):

| Tool | What it does |
|------|--------------|
| `list_docs` | Lists the documents |
| `search_docs` | Finds which documents mention a word, with the matching lines |
| `read_doc` | Returns one document in full |

You ask Claude a question in plain English. Claude sees the tools, decides to
search for a word, reads the document it found, and answers from it.

**What runs where.** The server runs on Sherlock, in your session. It only
reads files and searches text, so no GPU is needed. You'll run Claude Code on
Sherlock too, from Sherlock's `claude-code` module, signed in with your
Stanford account. The AI model itself runs at Anthropic, so your questions and
any document text the tools return are sent there. Only point this at material
you're allowed to use with Stanford's Claude.

## 1. Start the server

In a Sherlock terminal:

```bash
sh_dev
cd ~/hpc-server-workshop/03-mcp-server
bash submit_server.sh
```

When it's ready it prints:

```
MCP server on sh04-18n31.int:45893
Docs: /home/users/<you>/hpc-server-workshop/03-mcp-server/docs (3 files)
Address written to /scratch/users/<you>/hpc_workshop_mcp.txt
```

Leave it running. Ctrl-C stops it.

## 2. Start Claude Code and connect it

Open a second Sherlock terminal and log in to the session's machine, as in
Tier 1 (the name is in the session's prompt). AI assistants like Claude Code
belong in a session, not on a login node:

```bash
ssh <machine>
cd ~/hpc-server-workshop/03-mcp-server
ml claude-code
```

Tell Claude Code about the server. This reads the server's address and your
token from their files, so there's nothing to copy:

```bash
claude mcp add --transport http workshop-docs "http://$(cat $SCRATCH/hpc_workshop_mcp.txt)/mcp" -H "x-token: $(cat ~/.hpc_workshop/token)"
```

Then start it:

```bash
claude
```

The first time, Claude Code asks you to sign in: choose your Stanford account,
open the link it shows in your laptop's browser, and paste back the code. Then
type `/mcp`: `workshop-docs` should be listed as connected, with three tools.

## 3. Ask it things

Ask about the workshop's documents:

- "Using the workshop docs, what should I do when a job dies with CUDA out of memory?"
- "Which workshop document covers loading a specific Python version, and what does it say?"
- "List the workshop documents and summarize each in one line."

Claude asks permission the first time it uses each tool, then shows which tool
it called and what came back. In testing it searched for "out of memory",
then read `gpu-jobs.md` and answered from it.

Now ask a Sherlock question without mentioning the workshop docs, such as
"What storage should I use for job output?". Claude Code on Sherlock already
reads Sherlock's own guidance for AI tools (`/etc/agents/`), and for a general
question like this it answers from those files instead of calling your tools.
That's how MCP works: you add tools, and Claude decides which source fits
the question.

## 4. Stop

`/exit` leaves Claude Code. Ctrl-C stops the server, and `exit` leaves the
session.

The server gets a new port each time it starts, so next time, update Claude
Code's entry before starting `claude`:

```bash
claude mcp remove workshop-docs
claude mcp add --transport http workshop-docs "http://$(cat $SCRATCH/hpc_workshop_mcp.txt)/mcp" -H "x-token: $(cat ~/.hpc_workshop/token)"
```

## Troubleshooting

| What you see | Likely cause |
|---|---|
| `workshop-docs` shows as failed in `/mcp` | The server stopped, or restarted on a new port. Check its terminal, then remove and add it again (step 4) |
| `401` / "Missing or wrong token" | The token changed since you added the server. Remove and add it again |
| "OAuth session expired" | Your Claude Code sign-in ran out. Run `claude` and type `/login` |

## Connecting from your laptop instead

If you have Claude Code on your laptop, you can connect it to the same server
through an SSH tunnel, as in Tier 1. Get the address with
`cat $SCRATCH/hpc_workshop_mcp.txt` on Sherlock, then on your laptop:

```bash
ssh -S none -N -L 8080:<machine>:<port> login.sherlock.stanford.edu
```

and in another laptop terminal, with your token (`cat ~/.hpc_workshop/token`
on Sherlock) in place of `<token>`:

```bash
claude mcp add --transport http workshop-docs http://localhost:8080/mcp -H "x-token: <token>"
```

(This route was tested with direct requests through the tunnel, not yet from
Claude Code on a laptop.)

## Using your own documents

Point `DOCS_DIR` in `submit_server.sh` at your own folder of Markdown (`.md`)
files and the tools work unchanged. `search_docs` is a plain word match; for a
large collection you'd replace that one function with a real search engine,
and Claude would use it the same way.

If your documents can't go to Anthropic at all, the model has to run on
Sherlock too, for example with Ollama from Tier 2; see Sherlock's docs on
[AI coding agents][agents]. Expect worse results: small models are much less
reliable at choosing and chaining tools than Claude.

[agents]: https://www.sherlock.stanford.edu/docs/software/ai/coding-agents/
