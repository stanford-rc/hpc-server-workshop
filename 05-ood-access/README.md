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

## Option B — Make an OnDemand app for your lab

Jupyter and the other apps on the dashboard are OnDemand **interactive apps**.
Each one is a small folder of files: `form.yml` (the start form),
`submit.yml.erb` (what the job asks for) and `script.sh.erb` (what the job
runs). Together they tell OnDemand how to start a job and how to connect your
browser to it.

You can make your own, for example one that starts the Tier 4 web server.
Copy an existing app, such as Sherlock's `sh_jupyterlab`, into
`~/ondemand/dev/<app name>/` and change it. It then shows up in OnDemand under
**Develop > My Sandbox Apps**, for you only.

To share it with your lab, put a copy of the folder somewhere your group can
read, such as `$GROUP_HOME`. Each labmate copies it into their own
`~/ondemand/dev/` and starts their own session from it. Their session runs as
them, with their own token and files, so they need to have done the same setup
first: the workshop files and a token (Tier 1, step 2).

Putting an app on everyone's dashboard, as an official Sherlock app, is
something SRC does.

---

## Choosing between Tier 4 and Tier 5

| | Tier 4 (SSH tunnel) | Tier 5 (OOD) |
|---|---|---|
| Setup on your laptop | SSH tunnel per session | None — just a browser |
| What talks to your server | Your laptop's browser, through the tunnel | A notebook or app on a compute node |
| Works with laptop-native tools | Yes (`localhost:8080`) | No |
| Good for | Driving a custom page you wrote | Notebooks, file transfer, existing apps |
| Sharing with a lab | Labmates use your server with a shared token | Each labmate runs their own copy of your app |

They work together: build your page with the Tier 4 tunnel, then make it an
OnDemand app once your lab wants to use it.

[ood]: https://ondemand.sherlock.stanford.edu
[ood_docs]: https://www.sherlock.stanford.edu/docs/user-guide/ondemand/
