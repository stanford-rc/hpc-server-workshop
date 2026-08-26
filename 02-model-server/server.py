"""
server.py — FastAPI model inference server (Tier 2).

Loads a HuggingFace text-generation model and exposes a /generate endpoint.
Writes its address to SERVER_ADDR_FILE on startup so batch clients can find it.

Default model: distilgpt2 (~300 MB, runs on CPU — good for testing).
For real work: set MODEL_NAME to a larger model and request a GPU in sbatch.

  export MODEL_NAME="meta-llama/Llama-3.2-1B"
  sbatch submit_server.sh   # requests --gpus=1

HuggingFace cache: set HF_HOME to $SCRATCH or $OAK so models persist across jobs.
  export HF_HOME="$SCRATCH/hf_cache"

Start manually:
  python server.py

Via SLURM:
  sbatch submit_server.sh
"""

import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import GenerationConfig, pipeline

MODEL_NAME = os.environ.get("MODEL_NAME", "distilgpt2")
ADDR_FILE = Path(os.environ.get("SERVER_ADDR_FILE", "/tmp/hpc_workshop_model.txt"))
PORT = int(os.environ.get("PORT", 8081))

generator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global generator
    print(f"Loading model: {MODEL_NAME} ...")
    # device=0 uses the first GPU; device=-1 forces CPU.
    device = 0 if os.environ.get("CUDA_VISIBLE_DEVICES") else -1
    generator = pipeline("text-generation", model=MODEL_NAME, device=device)
    host = socket.getfqdn()
    ADDR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADDR_FILE.write_text(f"http://{host}:{PORT}")
    print(f"Model ready. Server address written to {ADDR_FILE}")
    yield


app = FastAPI(title="HPC Model Server", lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100
    temperature: float = 1.0


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/generate")
def generate(req: GenerateRequest):
    """Generate text continuation from a prompt.

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
    outputs = generator(req.prompt, generation_config=config)
    return {"generated_text": outputs[0]["generated_text"], "model": MODEL_NAME}


def main():
    uvicorn.run("server:app", host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
