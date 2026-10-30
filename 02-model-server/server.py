"""
server.py — FastAPI model inference server (Tier 2).

Brad Rittenhouse, Stanford Research Computing (bcritt@stanford.edu)

Loads a Hugging Face text-generation model and answers prompts at /generate.
On startup it picks a free port and writes "<machine>:<port>" to
SERVER_ADDR_FILE so a client can find it. Every request must include the token
from TOKEN_FILE, as in Tier 1.

MODEL_NAME picks the model; it must be a chat model (one trained to answer
instructions), since each prompt is sent as a chat message. The default,
Qwen2.5-1.5B-Instruct, fits on a GPU slice.

Start it:
  bash submit_server.sh      # inside an sh_dev session
  sbatch submit_server.sh    # or as a batch job
"""

import os
import secrets
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from transformers import GenerationConfig, pipeline

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_model.txt"))
# 0.0.0.0 = accept connections from any machine on Sherlock; the token keeps
# everyone else out.
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
TOKEN_FILE = Path(os.path.expanduser(os.environ.get("TOKEN_FILE", "~/.hpc_workshop/token")))


def pick_port() -> int:
    """Return $PORT if set, else a port nobody on this machine is using."""
    override = os.environ.get("PORT")
    if override:
        return int(override)
    with socket.socket() as probe:
        probe.bind(("", 0))  # port 0 = let the system pick a free one
        return probe.getsockname()[1]


PORT = pick_port()

if not TOKEN_FILE.exists():
    raise SystemExit(f"No token file at {TOKEN_FILE}. Make one first (see the Tier 1 README).")
TOKEN = TOKEN_FILE.read_text().strip()
token_header = APIKeyHeader(name="x-token", auto_error=False)


def require_token(given: str | None = Security(token_header)):
    if not given or not secrets.compare_digest(given, TOKEN):
        raise HTTPException(status_code=401, detail="Missing or wrong token")

generator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global generator
    print(f"Loading model: {MODEL_NAME} ...", flush=True)
    # device=0 uses the first GPU; device=-1 forces CPU.
    device = 0 if os.environ.get("CUDA_VISIBLE_DEVICES") else -1
    # torch_dtype="auto": load the model in the precision it was saved in (half
    # precision here), which takes half the GPU memory of the default.
    generator = pipeline("text-generation", model=MODEL_NAME, device=device, torch_dtype="auto")
    node = socket.gethostname()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"{node}:{PORT}")
    print(f"Model ready on {node}:{PORT}. Address written to {ADDR_FILE}", flush=True)
    yield


app = FastAPI(title="HPC Model Server", lifespan=lifespan, dependencies=[Depends(require_token)])


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100
    temperature: float = 0.7  # lower = more predictable answers


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/generate")
def generate(req: GenerateRequest):
    """Answer one prompt.

    The prompt is sent as a chat message, so the model answers it rather than
    just continuing the text. The reply is the last message in the output.

    Generation parameters go in a single GenerationConfig rather than as loose
    keyword arguments. The pipeline always supplies a `generation_config` of its
    own when the caller doesn't (transformers/pipelines/text_generation.py:400),
    so loose kwargs are always *mixed* with one — which transformers 5
    deprecates: "pass either a `generation_config` object OR all generation
    parameters explicitly, but not both."

    A config passed here takes precedence over the pipeline's default, and
    anything left unset is filled in from the model's own config.
    """
    config = GenerationConfig(
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        do_sample=True,
    )
    outputs = generator([{"role": "user", "content": req.prompt}], generation_config=config)
    reply = outputs[0]["generated_text"][-1]["content"]
    return {"generated_text": reply, "model": MODEL_NAME}


def main():
    uvicorn.run(app, host=BIND_HOST, port=PORT)


if __name__ == "__main__":
    main()
