# -*- coding: utf-8 -*-
"""Pacerul adaptiv: testele care GARANTEAZA anti-dependenta prin constructie.
Semnatura: engagement perfect NU prelungeste sesiunea — o incheie la buget."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adaptive_pacer import AdaptivePacer, AdaptivePacer as AP, MISSIONS


def test_STRUCTURAL_niciun_dark_pattern_in_cod():
    # garda structurala: nicio notiune de streak public/recompensa/prelungire
    attrs = set(dir(AdaptivePacer))
    for forbidden in ("streak", "badge", "reward", "extend", "extend_session",
                      "notify", "push_notification", "daily_goal"):
        assert forbidden not in attrs, f"dark pattern interzis: {forbidden}"


def test_SEMNATURA_engagement_perfect_NU_prelungeste_sesiunea():
    # copil perfect engaged: raspunde corect mereu. Software-ul care creeaza
    # dependenta ar continua. Al nostru INCHIDE sesiunea la buget, cu misiune.
    p = AdaptivePacer(budget_turns=8)
    d = None
    for _ in range(8):
        d = p.observe(correct=True, response_time_s=3.0)
    assert d.action == "end_session"
    assert d.offline_mission                      # pleaca cu o misiune offline
    # si dupa incheiere, nu exista continuare — oricat ar insista
    d2 = p.observe(correct=True)
    assert d2.action == "end_session" and d2.turns_left == 0


def test_struggle_relaxeaza_IMEDIAT_fara_histerezis():
    p = AdaptivePacer(difficulty=3, budget_turns=20)
    d1 = p.observe(correct=False)                 # PRIMA greseala relaxeaza deja
    assert d1.action == "simplify" and d1.difficulty == 2
    d2 = p.observe(correct=False)                 # a doua relaxeaza din nou
    assert d2.action == "simplify" and d2.difficulty == 1


def test_avansarea_cere_consistenta_nu_o_tura_norocoasa():
    p = AdaptivePacer(difficulty=2, budget_turns=30)
    d = p.observe(correct=True)                   # o singura tura buna
    assert d.action != "advance"                  # histerezis: nu urcam inca
    for _ in range(6):
        d = p.observe(correct=True)
    assert p.difficulty >= 3                      # consistenta => avanseaza


def test_copil_lent_dar_corect_avanseaza_la_fel():
    # ritmul e normalizat la mediana PROPRIE: lent-constant nu e penalizat
    lent = AdaptivePacer(difficulty=2, budget_turns=30)
    for _ in range(7):
        d = lent.observe(correct=True, response_time_s=20.0)  # mereu lent, mereu corect
    assert lent.difficulty >= 3                   # avanseaza identic cu un copil rapid


def test_incetinirea_brusca_fata_de_propriul_ritm_tempereaza():
    p = AdaptivePacer(budget_turns=30)
    for _ in range(4):
        p.observe(correct=True, response_time_s=5.0)
    m_before = p.mastery
    p.observe(correct=True, response_time_s=60.0)  # 12x propria mediana: distras?
    assert p.mastery < m_before + 0.2              # scorul turei a fost temperat


def test_misiunea_offline_exista_pe_toate_nivelurile_si_limbile():
    for lang in ("ro", "en"):
        for lvl in range(1, 6):
            assert len(MISSIONS[lang][lvl]) > 20


def test_sesiunea_urmatoare_incepe_cu_misiunea_offline():
    p = AdaptivePacer(budget_turns=2, lang="ro")
    p.observe(correct=True)
    d = p.observe(correct=True)                   # bugetul se termina
    assert d.action == "end_session"
    urmatoarea = AdaptivePacer(last_mission=d.offline_mission, lang="ro")
    g = urmatoarea.greeting()
    assert d.offline_mission in g                 # lumea reala e primul subiect
    assert "misiune" in g


def test_ajutorul_cerut_e_ok_dar_tempereaza_avansarea():
    p = AdaptivePacer(difficulty=2, budget_turns=30)
    for _ in range(7):
        p.observe(correct=True, asked_for_help=True)
    # cu ajutor constant, stapanirea creste mai greu decat fara
    q = AdaptivePacer(difficulty=2, budget_turns=30)
    for _ in range(7):
        q.observe(correct=True, asked_for_help=False)
    assert q.mastery > p.mastery
