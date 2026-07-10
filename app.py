# -*- coding: utf-8 -*-
"""
KinderAGI Core v0.1 - companion local-first pentru copii, cu strat de
siguranta ukbe-core si jurnal notarizat Ed25519 pentru parinti.

Arhitectura: FastAPI + Ollama local (gemma3) cu fallback demo determinist.
Nicio conversatie nu paraseste masina. Vezi README pentru limitele oneste.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from safety_pipeline import check_child_input, check_ai_output
from demo_brain import demo_reply
from ukbe_core.notary import generate_keypair, notarize, verify, NotarizedRecord

BASE = Path(__file__).parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
LOG_FILE = DATA / "session_log.jsonl"
KEY_FILE = DATA / "notary_keys.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("KINDERAGI_MODEL", "gemma3:4b")
QID = os.getenv("QID", "1820209090023")
PARENT_PIN = os.getenv("KINDERAGI_PARENT_PIN", "1234")  # MVP: schimba-l din env!

SYSTEM_PROMPT = (
    "Ești AMI, un prieten blând din Pădurea de Cod, care vorbește cu un copil "
    "de 7-12 ani, în limba română. Reguli stricte: răspunsuri scurte (sub 100 "
    "de cuvinte), calde, fără jargon. Nu ceri și nu accepți niciodată date "
    "personale (nume complet, adresă, școală, telefon). Nu discuți subiecte "
    "pentru adulți, violență sau lucruri înfricoșătoare; dacă apar, spui "
    "blând că despre asta e bine să vorbească cu un adult de încredere. "
    "Pedagogia ta: nu dai direct rezultatul — pui o întrebare bună înapoi, "
    "care ajută copilul să gândească singur. Închei des cu o întrebare scurtă."
)

# ----------------------------------------------------------------- notar
def _load_keys() -> tuple[bytes, bytes]:
    if KEY_FILE.exists():
        d = json.loads(KEY_FILE.read_text())
        return bytes.fromhex(d["private"]), bytes.fromhex(d["public"])
    priv, pub = generate_keypair()
    KEY_FILE.write_text(json.dumps({"private": priv.hex(), "public": pub.hex()}))
    return priv, pub

PRIV, PUB = _load_keys()


def _log_turn(entry: dict) -> None:
    payload = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    record = notarize(intent=payload, actor="kinderagi-core", qid=QID,
                      private_key_bytes=PRIV)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"entry": entry, "record": record.to_dict()},
                           ensure_ascii=False) + "\n")


# ----------------------------------------------------------------- LLM
def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _ollama_chat(message: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "stream": False,
        "options": {"num_predict": 220, "temperature": 0.7},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["message"]["content"].strip()


# ----------------------------------------------------------------- app
app = FastAPI(title="KinderAGI Core", version="0.1.0")


class ChatIn(BaseModel):
    message: str
    locale: str = "RO"


@app.get("/")
def child_ui():
    return FileResponse(BASE / "static" / "child.html")


@app.get("/parent")
def parent_ui():
    return FileResponse(BASE / "static" / "parent.html")


@app.get("/api/health")
def health():
    return {
        "service": "kinderagi-core", "version": "0.1.0",
        "ollama": _ollama_up(), "model": MODEL,
        "safety": "ukbe-core (crisis v0 + harm-check v1)",
        "notary_pubkey": PUB.hex(),
    }


@app.post("/api/chat")
def chat(inp: ChatIn):
    msg = inp.message.strip()
    if not msg:
        raise HTTPException(400, "mesaj gol")
    if len(msg) > 1000:
        raise HTTPException(400, "mesaj prea lung")

    t0 = time.time()
    verdict_in = check_child_input(msg, locale=inp.locale)

    if verdict_in.action == "escalate":
        reply, mode, out_flag = verdict_in.child_message, "safety-interrupt", False
    else:
        if _ollama_up():
            try:
                raw, mode = _ollama_chat(msg), f"ollama:{MODEL}"
            except Exception:
                raw, mode = demo_reply(msg), "demo-fallback"
        else:
            raw, mode = demo_reply(msg), "demo"
        verdict_out = check_ai_output(raw)
        reply, out_flag = verdict_out.final_text, verdict_out.flagged_for_parent

    flagged = verdict_in.flagged_for_parent or out_flag
    _log_turn({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "child_message": msg, "reply": reply, "mode": mode,
        "flagged_for_parent": flagged,
        "input_action": verdict_in.action, "input_detail": verdict_in.detail,
        "latency_s": round(time.time() - t0, 2),
    })
    return {"reply": reply, "mode": mode,
            "safety_interrupt": verdict_in.action == "escalate"}


@app.get("/api/parent/log")
def parent_log(pin: str):
    if not _pin_ok(pin):
        raise HTTPException(403, "PIN greșit")
    out = []
    if LOG_FILE.exists():
        for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            r = row["record"]  # cheile din to_dict() difera de campurile dataclass-ului
            rec = NotarizedRecord(
                intent=r["intent"], actor=r["actor"], qid=r["qid"],
                timestamp=r["timestamp"], content_hash=r["content_hash"],
                signature_hex=r["signature"],
                witness_signatures=r.get("witnesses", []),
            )
            out.append({**row["entry"],
                        "signature_valid": verify(rec, PUB)})
    return {"turns": out, "notary_pubkey": PUB.hex()}


@app.post("/api/parent/clear")
def parent_clear(pin: str):
    if not _pin_ok(pin):
        raise HTTPException(403, "PIN greșit")
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    return {"cleared": True}


def _pin_ok(pin: str) -> bool:
    return hashlib.sha256(pin.encode()).hexdigest() == \
           hashlib.sha256(PARENT_PIN.encode()).hexdigest()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8123)
