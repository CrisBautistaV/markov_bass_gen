"""
markovgen.py
============
Markov chain-based pitch generation for BassGen.

This module drives melodic motion using a first-order Markov chain over
*scale-degree intervals* (semitones relative to the previous note).
Rather than choosing pitches directly, the engine chooses how far to move
from the last note, which naturally creates smooth, idiomatic bass lines.

Design notes
------------
- Intervals are scale-degree steps, not raw semitones, so the same
  transition table works in any key or mode.
- Harmonic acceptance (``harmonic_acceptance``) acts as a filter:
  candidates that fall outside the current chord or scale are discarded
  and a new interval is sampled.  On strong beats only chord tones are
  accepted; on weak beats scale tones are also allowed.
- If no valid candidate is found within ``max_tries`` attempts the engine
  stays on the previous note (safe fallback with no audible glitch).
"""

import random


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------

# Each key is an interval that was *just played*.
# Each value is a dict {next_interval: probability}.
# Probabilities within a row should sum to 1.0 (they don't have to, but
# random.choices normalises automatically).
#
# Interpretation of interval values (semitones):
#   0  = repeat the same note
#   1  = step up one semitone
#  -1  = step down one semitone
#   2  = step up a whole tone
#  -2  = step down a whole tone
#   5  = leap up a fourth
#  -5  = leap down a fourth
#   7  = leap up a fifth
#  -7  = leap down a fifth
#
# General tendencies encoded here:
#   - After staying still (0): prefer small stepwise motion.
#   - After a small step up (1): prefer to continue or reverse.
#   - After a large leap up (5, 7): strongly prefer to fall back by step.
#   - Mirror symmetry for downward versions of each interval.

MARKOV_INTERVAL_TRANSITIONS: dict[int, dict[int, float]] = {
    # prev  →  next : weight
    0:  { 1: 0.25, -1: 0.25,  2: 0.15, -2: 0.15,  0: 0.20 },

    1:  { 0: 0.30, -1: 0.35, -2: 0.20,  1: 0.15 },
   -1:  { 0: 0.30,  1: 0.35,  2: 0.20, -1: 0.15 },

    2:  { -1: 0.45, -2: 0.35,  0: 0.20 },
   -2:  {  1: 0.45,  2: 0.35,  0: 0.20 },

    5:  { -2: 0.50, -1: 0.30,  0: 0.20 },
   -5:  {  2: 0.50,  1: 0.30,  0: 0.20 },

    7:  { -2: 0.60, -1: 0.25,  0: 0.15 },
   -7:  {  2: 0.60,  1: 0.25,  0: 0.15 },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _choose_next_interval(prev_interval: int) -> int:
    """Sample the next interval from the Markov transition table.

    If ``prev_interval`` has no explicit row (e.g. a large leap that
    isn't listed), the row for interval 0 is used as a neutral default.

    Args:
        prev_interval: The interval (in semitones) that was just played.

    Returns:
        The next interval to apply to the current note.
    """
    row = MARKOV_INTERVAL_TRANSITIONS.get(
        prev_interval,
        MARKOV_INTERVAL_TRANSITIONS[0]   # default: treat as if coming to rest
    )
    intervals = list(row.keys())
    weights   = list(row.values())
    return random.choices(intervals, weights=weights, k=1)[0]


def _harmonic_acceptance(
    note: int,
    chord_pcs: list[int],
    scale_pcs: list[int],
    beat_strength: float
) -> bool:
    """Return True if *note* is harmonically appropriate for this beat.

    Args:
        note:         MIDI note number (0-127).
        chord_pcs:    Pitch classes (0-11) of the current chord.
        scale_pcs:    Pitch classes (0-11) of the current scale.
        beat_strength: 1.0 for strong beats (1 & 3 in 4/4),
                       0.5 for weak beats.  Only chord tones are
                       accepted on strong beats; scale tones are also
                       accepted on weak beats.

    Returns:
        True if the note should be played, False if it should be rejected.
    """
    pc = note % 12
    if beat_strength == 1.0:
        return pc in chord_pcs
    if beat_strength == 0.5:
        return pc in chord_pcs or pc in scale_pcs
    # fallback: accept anything in the scale
    return pc in scale_pcs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initial_bass_note(chord_midi_notes: list[int]) -> int:
    """Choose the starting note for a new phrase.

    Selects the lowest available chord tone so the bass line begins
    on a harmonically stable, root-position anchor.

    Args:
        chord_midi_notes: MIDI note numbers belonging to the current chord
                          (as returned by ``pitch.get_chord_midi_notes``).

    Returns:
        The lowest MIDI note in the chord.
    """
    return min(chord_midi_notes)


def next_bass_note(
    prev_note: int,
    prev_interval: int,
    chord_pcs: list[int],
    scale_pcs: list[int],
    beat_strength: float,
    low: int = 36,
    high: int = 60,
    max_tries: int = 30
) -> tuple[int, int]:
    """Generate the next bass note using the Markov interval engine.

    Samples a candidate interval from the transition table, applies it
    to ``prev_note``, and accepts the result only if it passes range and
    harmonic checks.  Up to ``max_tries`` candidates are tested; if none
    pass, the previous note is returned unchanged (interval = 0).

    Args:
        prev_note:      MIDI note number of the last played note.
        prev_interval:  Interval (semitones) that produced ``prev_note``.
        chord_pcs:      Pitch classes of the current chord (0-11).
        scale_pcs:      Pitch classes of the current scale (0-11).
        beat_strength:  1.0 for strong beats, 0.5 for weak beats.
        low:            Minimum allowed MIDI note (default: C2 = 36).
        high:           Maximum allowed MIDI note (default: C4 = 60).
        max_tries:      Maximum rejection-sampling attempts before falling back.

    Returns:
        A tuple ``(next_note, interval_used)`` where ``interval_used``
        should be passed back as ``prev_interval`` on the next call.
    """
    for _ in range(max_tries):
        interval  = _choose_next_interval(prev_interval)
        candidate = prev_note + interval

        if not (low <= candidate <= high):
            continue  # out of bass range — try again

        if _harmonic_acceptance(candidate, chord_pcs, scale_pcs, beat_strength):
            return candidate, interval

    # Fallback: no valid candidate found — hold the current note.
    return prev_note, 0
