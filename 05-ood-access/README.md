# Tier 5: Open OnDemand (no tunnel)

Tier 4 reaches a compute-node server by forwarding a port to your laptop.
[Open OnDemand][ood] removes that step: an OOD session *already runs on a
compute node*, and your browser is already connected to it. Anything on the
cluster network is reachable from inside the session with no SSH tunnel at all.

That makes OOD the least-plumbing option, and usually the right first
recommendation for a researcher who just wants to look at their results.

Connect at **https://ondemand.sherlock.stanford.edu** (SUNet ID + 2FA).

## What OOD gives you for free

Before building anything, check whether an existing interactive app already
covers the need — no code required:

| Interactive App | Use it for |
|---|---|
| **Jupyter / JupyterLab** | Query your server, plot results, iterate in notebooks |
| **code-server** (VS Code) | Edit code on the cluster in a browser |
| **RStudio Server** | R analysis with plots |
| **TensorBoard** | Training curves |
| **Interactive Desktop** | A full desktop — run a normal browser *on the cluster* |
| **File Explorer** | Browse, view, upload, and download files directly |

For "I just want to get my results onto my laptop," the **Files** menu already
does upload/download without any of the machinery in Tier 4.

See the [Sherlock OnDemand docs][ood_docs] for the full list and screenshots.

---

## Option A — Query your server from a notebook

Start an **Interactive Apps > Jupyter Notebook** session, leaving everything
on the start form as it is. Then read the address file your server wrote and
call it directly. The notebook runs on a compute node, so it can reach your server with no tunnel. Send your token, as
every client does:

```python
import os
from pathlib import Path
import requests

addr = Path(os.path.expandvars("$SCRATCH/hpc_workshop_gui.txt")).read_text().strip()
headers = {"x-token": Path("~/.hpc_workshop/token").expanduser().read_text().strip()}

print(requests.get(f"http://{addr}/health", headers=headers).json())

# List the results
for f in requests.get(f"http://{addr}/api/results", headers=headers).json():
    print(f["name"], f["size_bytes"])
```

The same works for the Tier 1 and Tier 2 servers (`hpc_workshop_server.txt`,
`hpc_workshop_model.txt`). Ollama is the exception: it only accepts
connections from its own machine.

## Option B — Reach your own page with the Interactive Desktop

Start **Interactive Apps > Interactive Desktop**, open the browser inside that
desktop session, and go to `http://<node>:<port>` using the values from your
discovery file. You are browsing from *inside* the cluster, so the node
hostname resolves — the same URL that fails from your laptop can work here.

Paste your token into the page as in Tier 4.

## Option C — Publish it as a custom interactive app

The above options are for *you*. If you want colleagues to launch your tool
from the OOD dashboard the way they launch Jupyter, that means packaging it as
a **custom OOD interactive app**: a small directory of templates (`form.yml`,
`submit.yml.erb`, `script.sh.erb`) that tells OOD how to submit the job and
where to connect. Researchers do build these on Sherlock — usually starting
from the `sh_jupyterlab` template — and it's the real answer to "I want a site
my lab can use."

It's also the option that needs SRCC involvement: app deployment, and any
proxying of your app's port through the OOD portal, is configured on the
service side. **Contact SRCC** to scope it.

> **What this workshop deliberately doesn't claim.** There is no documented,
> general-purpose way to proxy an arbitrary port on a compute node through the
> Sherlock OOD portal to your laptop's browser. OOD's own apps do exactly that,
> but through per-app configuration. If you need it, ask SRCC rather than
> guessing at a URL pattern.

---

## Choosing between Tier 4 and Tier 5

| | Tier 4 (SSH tunnel) | Tier 5 (OOD) |
|---|---|---|
| Setup on your laptop | SSH tunnel per session | None — just a browser |
| Where the browser runs | Your laptop | A compute node |
| Works with laptop-native tools | Yes (`localhost:8080`) | No |
| Good for | Driving a custom page you wrote | Notebooks, file transfer, existing apps |
| Sharing with a lab | No | Yes, via a custom app (with SRCC) |

They compose: develop against the Tier 4 tunnel, then package as an OOD app
once it's worth sharing.

[ood]: https://ondemand.sherlock.stanford.edu
[ood_docs]: https://www.sherlock.stanford.edu/docs/user-guide/ondemand/
