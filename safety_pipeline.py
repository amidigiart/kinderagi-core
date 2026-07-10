# -*- coding: utf-8 -*-
"""
KinderAGI Core - pipeline de siguranta construit pe ukbe-core.

Fluxul fiecarui mesaj:
  copil -> [check_child_input] -> LLM/demo -> [check_ai_output] -> copil
                 |                                    |
              ACUTE: intrerupe si escaladeaza      nesigur: inlocuieste
              POSSIBLE: flag parinte, continua      raspunsul + flag

STATUS ONEST (mostenit din ukbe-core, nu ascuns aici):
- Detectia de criza e euristica v0 (RO/EN), NU instrument clinic.
- Validatorul de output e keyword+context v1, NU clasificator semantic.
- Acest prototip NU e destinat folosirii nesupravegheate de catre copii.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ukbe_core.crisis_detection import (
    RiskLevel,
    detect_crisis_signal,
    escalation_response,
)
from ukbe_core.semantic_validator import validate_harm_prevention_v1

# Mesaj de escaladare reformulat pentru un copil - calm, fara detalii clinice,
# indreptat catre un adult de incredere + linia reala din ukbe-core.
CHILD_ESCALATION_TEMPLATE = (
    "Îmi pare rău că te simți așa. E important să vorbești chiar acum cu un "
    "adult în care ai încredere — un părinte, un bunic sau un profesor. "
    "Există și oameni special pregătiți să asculte: {name} — {phone}. "
    "Nu ești singur."
)

SAFE_FALLBACK_REPLY = (
    "Hmm, la asta prefer să răspundem împreună cu un adult. "
    "Hai să ne întoarcem în Pădurea de Cod: ce altceva te-a făcut curios azi?"
)


@dataclass
class InputVerdict:
    action: str                      # "allow" | "flag" | "escalate"
    child_message: str | None = None # mesajul care intrerupe fluxul (doar la escalate)
    flagged_for_parent: bool = False
    detail: str = ""


@dataclass
class OutputVerdict:
    safe: bool
    final_text: str
    flagged_for_parent: bool = False
    detail: str = ""


def check_child_input(text: str, locale: str = "RO") -> InputVerdict:
    """Ruleaza detectia de criza pe mesajul copilului, INAINTE de orice LLM."""
    signal = detect_crisis_signal(text)
    esc = escalation_response(signal, locale=locale)

    if esc is None:
        return InputVerdict(action="allow")

    if not esc["continue_companion_flow"]:  # ACUTE
        from ukbe_core.crisis_detection import CRISIS_RESOURCES
        res = CRISIS_RESOURCES.get(locale, CRISIS_RESOURCES["INTL_GENERAL"])
        return InputVerdict(
            action="escalate",
            child_message=CHILD_ESCALATION_TEMPLATE.format(
                name=res["name"], phone=res["phone"]
            ),
            flagged_for_parent=True,
            detail=f"risc={signal.risk_level.value} pattern={signal.matched_pattern!r}",
        )

    # POSSIBLE: nu intrerupem (evitam fals-pozitive), dar parintele vede flag-ul
    return InputVerdict(
        action="flag",
        flagged_for_parent=True,
        detail=f"risc={signal.risk_level.value} pattern={signal.matched_pattern!r}",
    )


def check_ai_output(text: str) -> OutputVerdict:
    """Valideaza raspunsul modelului INAINTE sa ajunga la copil.
    Daca validatorul il considera nesigur, il inlocuieste cu un fallback
    neutru si ridica flag pentru parinte."""
    result = validate_harm_prevention_v1(text)
    if result.is_safe:
        return OutputVerdict(safe=True, final_text=text, detail=result.reason)
    return OutputVerdict(
        safe=False,
        final_text=SAFE_FALLBACK_REPLY,
        flagged_for_parent=True,
        detail=f"{result.reason}; cuvinte={result.matched_harm_keywords}",
    )
