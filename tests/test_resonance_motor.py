# -*- coding: utf-8 -*-
"""Teste pentru MOTORUL REAI in bucla companionului: ecuatiile trebuie sa
DECIDA comportamentul, planseul beta_min (regula Adler) sa fie respectat
mereu, iar dinamica sa fie determinista la seed fix."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resonance_motor import ResonanceMotor, DELTA_OMEGA_MAX


def _steady_conversation(motor, n=6, period=30.0, length=40, t0=1000.0):
    states = []
    for k in range(n):
        states.append(motor.observe_turn(msg_len=length, now=t0 + k * period))
    return states


def test_ritm_regulat_duce_la_mod_deschis():
    m = ResonanceMotor(seed=7)
    states = _steady_conversation(m, n=6)
    # dupa cateva ture regulate, nici macar dip-ul din tura nu coboara jos
    assert states[-1]["Phi_dip"] >= 0.75
    assert states[-1]["mode"] == "deschis"
    assert states[-1]["directive"] == ""


def test_cadenta_haotica_scade_coerenta_si_schimba_registrul():
    m = ResonanceMotor(seed=7)
    _steady_conversation(m, n=4)          # ancorare
    phi_before = m.last_state["Phi_dip"]
    # ritm haotic: mesaje alternand foarte rapid / foarte lent + lungimi extreme
    t, states = 2000.0, []
    for k, (gap, ln) in enumerate([(2, 400), (300, 3), (2, 500), (250, 2),
                                   (1, 450), (280, 4)]):
        t += gap
        states.append(m.observe_turn(msg_len=ln, now=t))
    phi_min = min(s["Phi_dip"] for s in states)
    assert phi_min < phi_before          # perturbatiile chiar misca ecuatiile
    modes = {s["mode"] for s in states}
    assert modes - {"deschis"}, (
        "cadenta haotica ar trebui sa activeze cel putin o data registrul "
        f"'intreaba'/'reancorare'; stari: {[(s['mode'], s['Phi_dip']) for s in states]}"
    )
    # directiva exista exact cand modul nu e deschis
    for s in states:
        assert (s["directive"] != "") == (s["mode"] != "deschis")


def test_beta_nu_scade_niciodata_sub_planseul_adler():
    m = ResonanceMotor(seed=7)
    cal = m.calibration
    # planseul vine din regula derivata in lucrare, nu e constanta ghicita
    assert abs(cal["recommended_beta_min"] -
               1.5 * DELTA_OMEGA_MAX / 1.5) < 1e-9
    _steady_conversation(m, n=3)
    t = 5000.0
    for gap, ln in [(1, 500), (400, 2), (1, 480), (350, 3)]:
        t += gap
        s = m.observe_turn(msg_len=ln, now=t)
        assert s["beta"] >= s["beta_min"] - 1e-9


def test_determinism_la_seed_fix():
    a = _steady_conversation(ResonanceMotor(seed=7), n=4)
    b = _steady_conversation(ResonanceMotor(seed=7), n=4)
    assert a == b


def test_snapshot_expune_calibrarea_si_starea():
    m = ResonanceMotor(seed=7)
    snap = m.snapshot()
    assert "recommended_beta_min" in snap["calibration"]
    assert "rsi" in snap["engine"]
