# KinderAGI Core v0.1

**Local-first AI companion prototype for children (7–12), with a tested safety
layer (ukbe-core) and an Ed25519-notarized parent journal. No conversation
ever leaves the machine.**

*Română mai jos · Prototype status: development/demo — **NOT for unsupervised
use by real children.***

## Architecture

```
child ── /api/chat ──► [crisis check (ukbe-core v0)] ──► Ollama gemma3 (local)
                              │ ACUTE: interrupt +            │ (fallback: deterministic
                              ▼ real crisis resources         ▼  demo mode, labeled)
                        parent flag                [harm-check v1 on output]
                                                              │ unsafe: replaced + flag
                                                              ▼
                                    signed JSONL journal (Ed25519, ukbe-core notary)
                                                              │
                                              /parent — PIN + per-row signature verify
```

- **Input safety:** `detect_crisis_signal` (RO/EN heuristic v0) — ACUTE
  interrupts the flow and shows real crisis resources; POSSIBLE flags for the
  parent without breaking the conversation (false-positive care).
- **Output safety:** `validate_harm_prevention_v1` — harm keywords without
  protective context ⇒ reply replaced with a neutral fallback + parent flag.
- **Transparency:** every turn is notarized (Ed25519). The parent dashboard
  verifies each row's signature — a tampered journal shows ✗.
- **Privacy by construction:** local Ollama model, local log, zero external APIs.

## Run

```bash
pip install -r requirements.txt
pip install -e ../ukbe-core          # safety + notary modules
python app.py                        # http://127.0.0.1:8123
```

Ollama optional but recommended: `ollama pull gemma3:4b` and have Ollama
running. Without it, the app runs in a clearly-labeled deterministic
"story mode" (no AI).

Parent dashboard: `http://127.0.0.1:8123/parent` — default PIN `1234`;
set `KINDERAGI_PARENT_PIN` env var to change it (do this!).

```bash
pytest tests/        # safety pipeline + notary tamper-detection tests
```

## What is honestly NOT here yet

- Crisis detection is a **v0 text heuristic (RO/EN)** — not clinically
  validated; false negatives and false positives are both possible (see
  ukbe-core module docstrings, kept verbatim).
- The LLM system prompt is a policy, **not a guarantee** — a 4B local model
  can still produce unsuitable content; the output filter is keyword+context
  v1, not a semantic classifier.
- No age verification, no parental-consent flow, no content rating pipeline —
  all required before any real-child deployment (GDPR-K / EU AI Act Art. 5+52
  analysis pending, see ukbe-core COMPLIANCE.md for the honest mapping).
- PIN auth is single-factor and local-network only. Run on localhost.

## Status / Roadmap

v0.1 = the integration proof: April-2026 kinderagi skeleton + July-2026
ukbe-core immune system, stitched and tested. Next: parental consent flow,
clinically-reviewed pattern lists, model content-tuning, NLnet proposal.

---

© 2026 Mihai Roșca · Apache-2.0 (aligned with ukbe-core open-core licensing)
