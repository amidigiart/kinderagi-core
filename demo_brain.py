# -*- coding: utf-8 -*-
"""
Modul demo (fara LLM): raspunsuri deterministe in stilul Padurii de Cod,
folosit cand Ollama nu ruleaza. NU pretinde a fi AI - o spune explicit.
Pedagogia: intrebarea buna naste intrebarea urmatoare (cf. Cap. 1, Amidor).
"""
from __future__ import annotations

import random

_OPENERS = [
    "Ce întrebare bună! În Pădurea de Cod, o întrebare bună face lumina să crească.",
    "Îmi place cum gândești. Hai să ne uităm împreună.",
    "Asta e o întrebare de explorator adevărat.",
]

_TOPIC_HINTS = {
    "calculator": "Un calculator face exact ce îi spui — nici mai mult, nici mai puțin. De aceea contează CUM îi spui.",
    "robot": "Roboții par deștepți, dar ei urmează pași scriși de oameni. Cine scrie pașii are grijă și de reguli.",
    "ai": "Un AI învață din exemple, cam cum înveți tu din povești. Dacă exemplele sunt bune, răspunsurile sunt mai bune.",
    "cod": "Codul e o limbă pentru mașini. Ca orice limbă, o înveți cuvânt cu cuvânt — și greșind fără frică.",
    "internet": "Internetul e ca un oraș uriaș: locuri minunate, dar mergi cu un adult și nu dai nimănui datele tale.",
    "joc": "Jocurile bune se construiesc din reguli mici și clare. Vrei să inventăm împreună o regulă de joc?",
}

_CLOSERS = [
    "Tu ce crezi? Întreabă mai departe — Pădurea de Cod nu se închide niciodată.",
    "Ce te face cel mai curios la asta?",
    "Dacă ai putea testa un singur lucru, care ar fi?",
]

DEMO_NOTICE = "(mod poveste — fără AI real acum; pornește Ollama pentru conversație adevărată)"


def demo_reply(message: str) -> str:
    rng = random.Random(len(message))  # determinist pe acelasi input
    lower = message.lower()
    hint = next((h for k, h in _TOPIC_HINTS.items() if k in lower), None)
    parts = [rng.choice(_OPENERS)]
    if hint:
        parts.append(hint)
    else:
        parts.append(
            "Nu știu sigur răspunsul — și e în regulă să nu știi. "
            "Hai să formulăm împreună întrebarea și mai clar: ce anume vrei să afli mai întâi?"
        )
    parts.append(rng.choice(_CLOSERS))
    parts.append(DEMO_NOTICE)
    return " ".join(parts)
