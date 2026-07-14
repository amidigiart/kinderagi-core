# -*- coding: utf-8 -*-
"""
PACERUL ADAPTIV — software adaptiv de invatare cu PROTECTIA ATENTIEI gravata
in cod (Apache-2.0: pentru copii, stratul de siguranta TREBUIE sa fie auditabil
public — increderea parintilor nu se cere, se arata).

CE ADAPTEAZA (din semnale comportamentale simple, masurabile):
  - dificultatea urcă doar pe stapanire CONSISTENTA (histerezis: 3 ture bune
    la rand), dar coboara IMEDIAT la struggle — frustrarea e mai daunatoare
    decat plictiseala, deci relaxarea e mai rapida decat avansarea (asimetrie
    deliberata, acelasi principiu ca planseul beta_min: coborarea sub coerenta
    e tratata agresiv, urcarea e conservatoare).
  - timpul de raspuns e normalizat la MEDIANA COPILULUI INSUSI, nu la un
    standard: un copil lent-dar-corect avanseaza la fel ca unul rapid.

CE NU FACE, PRIN CONSTRUCTIE (testat structural, ca la arbitraj):
  - NU exista streaks, badges, recompense variabile, notificari de revenire —
    niciun camp si nicio metoda cu aceste nume (test de garda).
  - Sesiunea se TERMINA cand bugetul de atentie e consumat, indiferent cat de
    "engaged" e copilul — engagementul ridicat la finalul bugetului NU e un
    motiv de prelungire, e exact momentul in care software-ul care creeaza
    dependenta ar continua. Al nostru se opreste. Nu exista metoda de extindere.
  - Fiecare sesiune se incheie cu o MISIUNE OFFLINE (in lumea reala); sesiunea
    urmatoare incepe intreband despre ea. Offline-ul e activul principal,
    ecranul e doar puntea.

LIMITA ONESTA: estimarea de "stapanire" e o euristica din semnale de
comportament (corect/gresit, ritm, cereri de ajutor) — NU o evaluare
psihometrica si NU un instrument de diagnostic. Nu eticheteaza copii.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

MIN_DIFF, MAX_DIFF = 1, 5
ADVANCE_STREAK_NEEDED = 3      # ture consistent bune pentru a urca (histerezis)
MASTERY_UP, MASTERY_DOWN = 0.75, 0.40
DEFAULT_BUDGET_TURNS = 12      # bugetul de atentie al unei sesiuni (ture)
SMOOTH = 0.6                   # netezire exponentiala a estimarii

# misiuni offline pe niveluri (RO/EN) — puntea spre lumea reala
MISSIONS = {
    "ro": {
        1: "Găsește trei frunze cu forme diferite și adu-le data viitoare să-mi povestești despre ele.",
        2: "Numără câte ferestre are casa ta și gândește-te de ce unele camere au mai multe.",
        3: "Întreabă un om mare care e prima lui amintire și ascultă toată povestea, fără să întrerupi.",
        4: "Construiește ceva din lucruri care nu mai sunt folosite și dă-i un nume.",
        5: "Învață pe cineva mai mic decât tine un lucru pe care îl știi bine. Cum a fost să fii tu învățătorul?",
    },
    "en": {
        1: "Find three leaves with different shapes and bring them next time to tell me about them.",
        2: "Count how many windows your home has and think about why some rooms have more.",
        3: "Ask a grown-up about their earliest memory and listen to the whole story without interrupting.",
        4: "Build something out of things nobody uses anymore, and give it a name.",
        5: "Teach someone younger than you something you know well. How did it feel to be the teacher?",
    },
}

WELCOME_BACK = {
    "ro": "Bine ai revenit! Data trecută aveai o misiune: {mission} Cum a fost?",
    "en": "Welcome back! Last time you had a mission: {mission} How did it go?",
}


@dataclass
class PacerDecision:
    difficulty: int                       # nivelul recomandat pentru URMATORUL pas
    action: str                           # continue | simplify | advance | end_session
    turns_left: int                       # cate ture mai are bugetul de atentie
    mastery: float                        # estimarea euristica [0,1] (NU diagnostic)
    offline_mission: str | None = None    # setat DOAR la end_session
    note: str = ""


@dataclass
class AdaptivePacer:
    lang: str = "ro"
    difficulty: int = 1
    budget_turns: int = DEFAULT_BUDGET_TURNS
    last_mission: str | None = None       # misiunea sesiunii precedente (daca exista)

    turn: int = 0
    mastery: float = 0.5
    _advance_streak: int = 0
    _struggles_in_row: int = 0
    _response_times: list = field(default_factory=list)
    _ended: bool = False

    # ------------------------------------------------------------ sesiune
    def greeting(self) -> str:
        """Inceputul sesiunii: daca a existat o misiune offline, incepem cu ea —
        lumea reala e subiectul principal, nu ecranul."""
        if self.last_mission:
            return WELCOME_BACK[self.lang].format(mission=self.last_mission)
        return ""

    def observe(self, correct: bool, response_time_s: float = 0.0,
                asked_for_help: bool = False) -> PacerDecision:
        """O tura observata -> decizia de pacing pentru urmatoarea."""
        if self._ended:
            # sesiunea s-a terminat; nu exista prelungire, oricat de engaged
            return self._end(note="sesiunea s-a încheiat — ne vedem data viitoare")

        self.turn += 1

        # scorul turei: corect=1, gresit=0; ajutorul cerut e OK dar tempereaza
        score = 1.0 if correct else 0.0
        if asked_for_help:
            score *= 0.7

        # ritm relativ la PROPRIA mediana (copil lent-dar-constant nu e penalizat)
        if response_time_s > 0:
            self._response_times.append(response_time_s)
            med = statistics.median(self._response_times)
            if len(self._response_times) >= 3 and response_time_s > 2.5 * med:
                score *= 0.8   # mult peste ritmul PROPRIU => posibil pierdut/distras

        self.mastery = SMOOTH * self.mastery + (1 - SMOOTH) * score

        # bugetul de atentie: cand e consumat, sesiunea se termina. Punct.
        if self.turn >= self.budget_turns:
            return self._end(note="bugetul de atenție s-a terminat (prin design)")

        # struggle: relaxare IMEDIATA (frustrarea nu asteapta histerezis)
        if not correct:
            self._struggles_in_row += 1
            self._advance_streak = 0
        else:
            self._struggles_in_row = 0

        if self.mastery < MASTERY_DOWN or self._struggles_in_row >= 2:
            if self.difficulty > MIN_DIFF:
                self.difficulty -= 1
                return self._decision("simplify", "coborâm puțin — e loc de joacă, nu de frustrare")
            return self._decision("continue", "rămânem la început, cu răbdare")

        # avansare: doar pe consistenta (histerezis), niciodata pe o tura norocoasa
        if correct and self.mastery >= MASTERY_UP:
            self._advance_streak += 1
            if self._advance_streak >= ADVANCE_STREAK_NEEDED and self.difficulty < MAX_DIFF:
                self._advance_streak = 0
                self.difficulty += 1
                return self._decision("advance", "ești pregătit(ă) de un pas mai sus")

        return self._decision("continue", "")

    # ------------------------------------------------------------- intern
    def _decision(self, action: str, note: str) -> PacerDecision:
        return PacerDecision(difficulty=self.difficulty, action=action,
                             turns_left=max(0, self.budget_turns - self.turn),
                             mastery=round(self.mastery, 3), note=note)

    def _end(self, note: str) -> PacerDecision:
        self._ended = True
        mission = MISSIONS[self.lang][self.difficulty]
        self.last_mission = mission
        return PacerDecision(difficulty=self.difficulty, action="end_session",
                             turns_left=0, mastery=round(self.mastery, 3),
                             offline_mission=mission, note=note)
