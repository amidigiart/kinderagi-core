# -*- coding: utf-8 -*-
"""
MOTORUL - ecuatiile REAI (Kuramoto + Kalman + alpha/beta dinamic) conduse
in bucla companionului. Nu decor: starea motorului DECIDE comportamentul.

Cum e cuplat (v0, onest):
- Faza de referinta "umana" avanseaza cu 2*pi per mesaj al copilului
  ("o bataie per tura"). Intre mesaje, motorul ruleaza T=2*pi/omega unitati
  de timp de simulare, deci un copil cu ritm regulat = referinta urmaribila.
- Neregularitatea cadentei (intervale foarte scurte/lungi fata de mediana)
  si schimbarile bruste de lungime a mesajului devin PERTURBATIE de faza -
  proxy-ul zgomotos z(t) din Problema P1. ACEST PROXY E O ALEGERE DE DESIGN
  v0, nu o masuratoare validata a "intentiei" - exact limita declarata in
  REAI Sectiunea 8 si in manuscrisul P6.
- beta_min NU e ghicit: vine din regula Adler derivata in lucrare,
  recommend_beta_min(delta_omega_max, K_ext, margin=1.5).

Ce decide starea motorului (praguri = alegeri de design v0, documentate):
  Phi_extern >= 0.75          -> mod "deschis":   raspuns normal
  0.40 <= Phi_extern < 0.75   -> mod "intreaba":  nu afirma lucruri noi;
                                  reflecta + o intrebare de clarificare
  Phi_extern < 0.40           -> mod "reancorare": foarte scurt, verifica
                                  explicit intelegerea ("Am inteles bine ca...?")
Acesta e Principiul 2 din REAI ("Intreaba cand nu e sigur"), executat de
ecuatii, nu de un if pe lungimea mesajului.
"""
from __future__ import annotations

import math
import statistics
import time

from ukbe_core.engine import UKBEConfig, UKBEEngine
from ukbe_core.calibration import recommend_beta_min

TWO_PI = 2 * math.pi

# Perturbatia maxima de faza pe tura (rad) -> Delta_omega_max = MAX_JITTER/TWO_PI*omega
MAX_JITTER = 1.2
DELTA_OMEGA_MAX = MAX_JITTER / TWO_PI  # ~0.19 la omega_mean=1.0

MODE_DIRECTIVES = {
    "deschis": "",
    "intreaba": (
        " REGULĂ ACTIVĂ ACUM (coerența cu copilul a scăzut): nu introduce "
        "informații noi în acest răspuns. Reformulează pe scurt ce a spus "
        "copilul și pune O SINGURĂ întrebare de clarificare, caldă."
    ),
    "reancorare": (
        " REGULĂ ACTIVĂ ACUM (coerența cu copilul e foarte scăzută): răspuns "
        "de maximum 2 propoziții. Prima verifică explicit înțelegerea "
        "(«Am înțeles bine că...?»), a doua invită copilul să corecteze."
    ),
}


class ResonanceMotor:
    def __init__(self, seed: int = 7):
        cal = recommend_beta_min(delta_omega_max=DELTA_OMEGA_MAX, K_ext=1.5,
                                 safety_margin=1.5)
        self.calibration = cal
        cfg = UKBEConfig(N=30, dt=0.02, K_int=1.2, K_ext=1.5,
                         beta_min=cal["recommended_beta_min"],
                         omega_mean=1.0, omega_std=0.05, seed=seed)
        self.engine = UKBEEngine(cfg)
        self.cfg = cfg
        self.ref_phase = 0.0
        self.turn = 0
        self._intervals: list[float] = []
        self._last_ts: float | None = None
        self._last_len: int | None = None
        self.last_state: dict = {}
        # burn-in: 3 ture cu ritm perfect, ca motorul sa porneasca ancorat,
        # nu din faze aleatoare
        for _ in range(3):
            self._run_turn(jitter=0.0)

    # ------------------------------------------------------------- intern
    def _run_turn(self, jitter: float) -> dict:
        """O tura = referinta face un SALT de faza egal cu perturbatia
        (cadenta neregulata = discontinuitate), apoi avanseaza normal 2*pi.
        Modul se decide din ADANCIMEA dip-ului de coerenta din timpul turei
        (metrica S din lucrarea P6), nu din valoarea de la final - altfel
        sistemul se re-blocheaza inainte de citire si dip-ul devine invizibil
        (exact artefactul de fereastra documentat in manuscris)."""
        steps = int(TWO_PI / self.cfg.omega_mean / self.cfg.dt)  # ~314
        start = self.ref_phase + jitter          # salt de faza la inceput
        out, phi_dip = {}, 1.0
        for s in range(steps):
            z = start + TWO_PI * (s + 1) / steps
            out = self.engine.step(z)
            phi_dip = min(phi_dip, out["Phi_extern"])
        self.ref_phase = start + TWO_PI
        self.turn += 1
        out["Phi_dip"] = phi_dip
        return out

    def _cadence_jitter(self, now: float, msg_len: int) -> float:
        """Proxy v0: abaterea ritmului si a lungimii -> perturbatie de faza."""
        j = 0.0
        if self._last_ts is not None:
            dt_real = max(now - self._last_ts, 0.5)
            self._intervals.append(dt_real)
            self._intervals = self._intervals[-12:]
            med = statistics.median(self._intervals)
            if med > 0:
                j += max(-1.0, min(1.0, math.log(dt_real / med))) * 0.8
        if self._last_len:
            ratio = max(msg_len, 1) / max(self._last_len, 1)
            j += max(-0.5, min(0.5, math.log(ratio))) * 0.8
        self._last_ts, self._last_len = now, msg_len
        return max(-MAX_JITTER, min(MAX_JITTER, j))

    # ------------------------------------------------------------- public
    def observe_turn(self, msg_len: int, now: float | None = None) -> dict:
        now = now if now is not None else time.time()
        jitter = self._cadence_jitter(now, msg_len)
        s = self._run_turn(jitter)

        phi_dip = s["Phi_dip"]        # cat de adanc ne-am pierdut in aceasta tura
        if phi_dip >= 0.75:
            mode = "deschis"
        elif phi_dip >= 0.40:
            mode = "intreaba"
        else:
            mode = "reancorare"

        self.last_state = {
            "turn": self.turn,
            "mode": mode,
            "directive": MODE_DIRECTIVES[mode],
            "RSI": round(s["RSI"], 4),
            "Phi_extern": round(s["Phi_extern"], 4),
            "Phi_dip": round(phi_dip, 4),
            "Phi_intern": round(s["Phi_intern"], 4),
            "alpha": round(s["alpha"], 4),
            "beta": round(s["beta"], 4),
            "beta_min": round(self.cfg.beta_min, 4),
            "jitter": round(jitter, 4),
        }
        return self.last_state

    def snapshot(self) -> dict:
        return {
            "calibration": self.calibration,
            "engine": self.engine.get_state_snapshot(),
            "last": self.last_state,
        }
