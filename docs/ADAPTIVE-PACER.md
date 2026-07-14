# Adaptive Pacer — adaptive learning with attention protection enforced in code

**Why this is open (Apache-2.0), not vaulted:** it's children's software. The
safety and anti-addiction layer must be **publicly auditable** — parents' trust
is shown, not claimed. The monetizable layer for KinderAGI is content, hosting
and brand; the protection code is the credibility.

## What adapts

- **Difficulty rises only on consistent mastery** (hysteresis: 3 good turns in
  a row) but **drops immediately on struggle** — a deliberate asymmetry, the
  same principle as the β_min floor: frustration is treated aggressively,
  advancement conservatively. One lucky answer never advances a level.
- **Response time is normalized to the child's own median**, not a standard: a
  slow-but-correct child advances exactly like a fast one. Only a sudden
  slowdown *relative to their own rhythm* (possible distraction) tempers the
  turn's score.
- Asking for help is fine — it tempers advancement, it is never punished.

## What it refuses to do — by construction, with structural tests

- **No dark patterns:** no streaks, badges, variable rewards, return
  notifications, daily goals. A structural test asserts none of these names
  exist on the class.
- **The attention budget is a hard stop.** When the session budget is spent,
  the session ends — *even at peak engagement*. High engagement at the end of
  the budget is precisely when addictive software would continue; this one
  stops. There is **no extend method**. The signature test feeds a perfectly
  engaged child and asserts the session still closes.
- **Every session ends with an offline mission** (find three different leaves;
  ask a grown-up about their earliest memory…) and the **next session opens by
  asking about it**. The real world is the main asset; the screen is the bridge.

## Honest limit

The "mastery" estimate is a heuristic from behavioral signals
(correct/incorrect, rhythm, help requests) — **not** a psychometric assessment
and **not** a diagnostic instrument. It paces content; it never labels children.

## API

    from adaptive_pacer import AdaptivePacer
    p = AdaptivePacer(lang="ro", difficulty=1, budget_turns=12,
                      last_mission=previous_session_mission)
    p.greeting()                      # opens with the offline mission, if any
    d = p.observe(correct=True, response_time_s=4.0, asked_for_help=False)
    # d.action ∈ {continue, simplify, advance, end_session},
    # d.difficulty, d.turns_left, d.offline_mission (set at end_session)

Tested in `tests/test_adaptive_pacer.py` (9 tests, including the structural
no-dark-patterns guard and the peak-engagement-still-ends signature test).
