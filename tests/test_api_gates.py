# -*- coding: utf-8 -*-
"""Teste pentru portile de productie: rate limit, cod de acces, PIN prod."""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _fresh_app(monkeypatch, **env):
    for k in ["KINDERAGI_ENV", "KINDERAGI_ACCESS_CODE", "KINDERAGI_PARENT_PIN"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app as app_module
    return importlib.reload(app_module)


def test_pin_implicit_refuzat_in_productie(monkeypatch):
    with pytest.raises(RuntimeError):
        _fresh_app(monkeypatch, KINDERAGI_ENV="prod")


def test_cod_de_acces_blocheaza_fara_cod(monkeypatch):
    m = _fresh_app(monkeypatch, KINDERAGI_ACCESS_CODE="pilot2026")
    from fastapi.testclient import TestClient
    c = TestClient(m.app)
    r = c.post("/api/chat", json={"message": "salut"})
    assert r.status_code == 403
    # health ramane public (necesar pentru monitorizare)
    assert c.get("/api/health").status_code == 200


def test_rate_limit_intoarce_429(monkeypatch):
    m = _fresh_app(monkeypatch, KINDERAGI_ACCESS_CODE="x")
    from fastapi.testclient import TestClient
    c = TestClient(m.app)
    codes = [c.post("/api/chat", json={"message": "hi"}).status_code
             for _ in range(25)]
    assert 429 in codes  # peste 20/min pe acelasi IP


def teardown_module(module):
    """Reincarca app cu mediul curat, ca celelalte teste sa nu mosteneasca
    portile setate aici."""
    import os, importlib
    for k in ["KINDERAGI_ENV", "KINDERAGI_ACCESS_CODE", "KINDERAGI_PARENT_PIN"]:
        os.environ.pop(k, None)
    import app as app_module
    importlib.reload(app_module)
