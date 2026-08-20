"""
MAX 2.0 — REST API Server
FastAPI server exposing MAX over HTTP on localhost:8000
"""
import json
import os
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.logger import log
from core.memory import get_command_history, get_notes, get_pending_reminders

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_API_CFG = _cfg.get("api", {})
HOST = _API_CFG.get("host", "127.0.0.1")
PORT = _API_CFG.get("port", 8000)

app = FastAPI(
    title="M.A.X API",
    description="Machine Autonomous eXpert — REST Interface",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global reference to the MAX processor (set by main.py)
_process_query = None


def set_query_processor(fn):
    """Called by main.py to inject the query handler."""
    global _process_query
    _process_query = fn


# ── Models ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    speak: bool = False  # If True, also speak the response


class QueryResponse(BaseModel):
    query: str
    skill: str
    response: str
    timestamp: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "M.A.X",
        "version": "2.0",
        "status": "operational",
        "endpoints": ["/ask", "/status", "/history", "/notes", "/reminders"]
    }


@app.get("/status")
def status():
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "assistant": _cfg["user"].get("assistant_name", "MAX"),
        "user": _cfg["user"]["name"]
    }


@app.post("/ask", response_model=QueryResponse)
def ask_max(req: QueryRequest):
    if not _process_query:
        raise HTTPException(503, "MAX query processor not initialized")
    try:
        result = _process_query(req.query, speak=req.speak)
        return QueryResponse(
            query=req.query,
            skill=result.get("skill", "unknown"),
            response=result.get("speak", ""),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        log.error(f"API /ask error: {e}")
        raise HTTPException(500, str(e))


@app.get("/history")
def get_history(n: int = 20):
    return {"history": get_command_history(n)}


@app.get("/notes")
def get_all_notes():
    return {"notes": get_notes()}


@app.get("/reminders")
def get_all_reminders():
    return {"reminders": get_pending_reminders()}


# ── Server ────────────────────────────────────────────────────────────────────

def run_server():
    """Start the FastAPI server (blocking call — run in thread)."""
    log.info(f"Starting MAX API on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
