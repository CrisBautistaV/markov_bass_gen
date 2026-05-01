"""
rhythm.py
=========
Rhythm pattern definitions and utilities for BassGen.

Each rhythm pattern is a 16-element list representing one bar of 16th notes
in 4/4 time (``time4 = True``).  Each element is a *velocity weight* in [0, 1]:

    0.0  → no note (rest)
    0.3  → ghost note / very quiet hit
    0.5  → weak beat / subdivision
    0.7  → medium accent
    1.0  → strong beat / full accent

The fractional weights are multiplied by 127 at send time to produce a
MIDI velocity, so the pattern doubles as both a rhythmic gate and a
dynamic contour.

Time signatures
---------------
The module supports 4/4 (``time4 = True``, 16 steps of 16th notes) and
6/8 (``time4 = False``, 12 steps of 8th notes).  The active set of
patterns is selected at import time based on the ``time4`` flag.

Usage example::

    from rhythm import RHYTHM_PATTERNS, choose_rhythm_pattern, pattern_to_attacks

    pattern = RHYTHM_PATTERNS["habanera"]
    attacks = pattern_to_attacks(pattern)   # [0, 6, 12]
"""

import random


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

time4  = True  # True → 4/4 (16 steps);  False → 6/8 (12 steps per bar)
rhythm = 16    # number of 16th-note steps per bar (used externally)


# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

if time4:
    # ------------------------------------------------------------------
    # 4/4 patterns — 16 steps (one 16th note each)
    # Step index:      0  1    2    3    4    5    6    7    8  9   10   11   12   13   14   15
    # Beat number:     1  e    +    a    2    e    +    a    3  e   +    a    4    e    +    a
    # ------------------------------------------------------------------
    RHYTHM_PATTERNS: dict[str, list[float]] = {
        # Four quarter notes — classic walking root motion.
        "quarters":   [1, 0, 0,   0,   0.7, 0, 0,   0,   0.7, 0, 0,   0,   0.7, 0, 0,   0  ],

        # Alternating quarter/eighth pairs — standard 8th-note groove.
        "eighths":    [1, 0, 0.5, 0,   0.5, 0, 0.5, 0,   1,   0, 0.5, 0,   0.5, 0, 0.5, 0  ],

        # All upbeats — creates tension against a down-beat melody.
        "offbeat":    [0, 1, 0,   1,   0,   1, 0,   1,   0,   1, 0,   1,   0,   1, 0,   1  ],

        # Displaced accents — syncopated funk/soul feel.
        "syncopated": [1, 0, 0,   0.7, 0,   0.7, 0, 0,   1,   0, 0,   0.7, 0,   0, 0.7, 0  ],

        # Every step at varying dynamics — busy walking-bass texture.
        "walking":    [1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                       1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],

        # Downbeats only — minimal, open feel.
        "sparse":     [1, 0, 0,   0,   0,   0, 0,   0,   1,   0, 0,   0,   0,   0, 0,   0  ],

        # Cuban habanera clave: beat 1, dotted-quarter rest, beat 3+ offbeat.
        # Distinctive Afro-Cuban rhythmic cell widely used in Latin music.
        "habanera":   [1, 0, 0,   0,   0,   0, 0.3, 0,   0,   0, 0,   0,   1,   0, 0,   0  ],
    }

else:
    # ------------------------------------------------------------------
    # 6/8 patterns — 16 steps (used as pairs of 6/8 bars)
    # ------------------------------------------------------------------
    RHYTHM_PATTERNS = {
        "quarters":   [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "eighths":    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
        "offbeat":    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        "syncopated": [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        "walking":    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "sparse":     [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        "habanera":   [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    }


# ---------------------------------------------------------------------------
# Probability weights for automatic pattern selection
# ---------------------------------------------------------------------------

# Higher weight → more likely to be chosen by choose_rhythm_pattern().
# Weights do not need to sum to 1; random.choices normalises them.
RHYTHM_WEIGHTS: dict[str, float] = {
    "quarters":   0.25,
    "eighths":    0.20,
    "offbeat":    0.10,
    "syncopated": 0.25,
    "walking":    0.10,
    "sparse":     0.10,
    "habanera":   0.30,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def choose_rhythm_pattern() -> str:
    """Randomly select a pattern name, weighted by ``RHYTHM_WEIGHTS``.

    Returns:
        A key from ``RHYTHM_PATTERNS``.
    """
    names   = list(RHYTHM_PATTERNS.keys())
    weights = [RHYTHM_WEIGHTS[name] for name in names]
    return random.choices(names, weights=weights, k=1)[0]


def pattern_to_attacks(pattern: list[float]) -> list[int]:
    """Return step indices where a note attack occurs (weight > 0).

    Useful for visualisation and testing — gives a compact representation
    of where notes land in the bar.

    Args:
        pattern: A 16-element velocity-weight list from ``RHYTHM_PATTERNS``.

    Returns:
        List of step indices (0-based) with non-zero weight.

    Example::

        >>> pattern_to_attacks(RHYTHM_PATTERNS["habanera"])
        [0, 6, 12]
    """
    return [i for i, weight in enumerate(pattern) if weight > 0]
