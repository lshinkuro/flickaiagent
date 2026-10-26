import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app import agent

API_KEY = os.getenv("API_KEY")  # wajib diisi kalau di-deploy ke VPS

app = FastAPI(title="Flick AI Agent")


def cek_api_key(x_api_key: str | None = Header(default=None)):
    if API_KEY and not secrets.compare_digest(x_api_key or "", API_KEY):
        raise HTTPException(401, "API key salah")


class ChatIn(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
def health():
    return {"ok": True}


# def (bukan async) supaya panggilan Ollama yang blocking jalan di threadpool
@app.post("/chat", dependencies=[Depends(cek_api_key)])
def chat(body: ChatIn):
    try:
        jawaban, langkah = agent.jalankan_agent(body.message, body.session_id)
    except Exception as e:
        raise HTTPException(502, f"Gagal memanggil model: {e}")
    return {"answer": jawaban, "tool_calls": langkah}


@app.delete("/sessions/{session_id}", dependencies=[Depends(cek_api_key)])
def reset(session_id: str):
    agent.reset_session(session_id)
    return {"ok": True}


@app.get("/status", dependencies=[Depends(cek_api_key)])
def status():
    files = [f for f in os.listdir(agent.WORKDIR) if not f.startswith(".")]
    return {"workdir": agent.WORKDIR, "files": len(files), "model": agent.MODEL,
            "shell": agent.ALLOW_SHELL}
