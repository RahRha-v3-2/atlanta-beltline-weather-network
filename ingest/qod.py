"""Quality-of-data gate for WeatherXM health scores.

A minimum of 0 disables the gate. A minimum above 0 rejects a missing score:
an absent quality signal is not treated as a pass.
"""

from __future__ import annotations


def qod_accepts(score: float | None, minimum: float) -> bool:
    if minimum < 0 or minimum > 1:
        raise ValueError("QOD_MIN_SCORE must be between 0 and 1")
    if minimum <= 0:
        return True
    if score is None:
        return False
    return score >= minimum
