"""
pitch.py
========
Harmonic context utilities for BassGen.

This module converts symbolic music theory concepts (key, scale type,
chord degree, chord quality) into concrete MIDI note numbers that the
Markov engine and OSC sender can use directly.

Terminology used throughout
---------------------------
PC (Pitch Class):
    An integer 0-11 representing a note name independently of octave.
    C=0, C#/Db=1, D=2, … B=11.

Scale degree:
    0-based index into the scale.  Degree 0 is the tonic, degree 1 is
    the second scale note, etc.

MIDI note:
    Standard MIDI pitch number (0-127).  Middle C = 60 (C4).
    Bass range used in this project: 36 (C2) – 60 (C4).
"""


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Maps note names (including enharmonic equivalents) to pitch classes 0-11.
NOTE_TO_PC: dict[str, int] = {
    "C": 0,  "C#": 1, "Db": 1,
    "D": 2,  "D#": 3, "Eb": 3,
    "E": 4,
    "F": 5,  "F#": 6, "Gb": 6,
    "G": 7,  "G#": 8, "Ab": 8,
    "A": 9,  "A#": 10, "Bb": 10,
    "B": 11,
}

# Maps scale type names to their interval patterns (semitones from the root).
# All patterns have 7 degrees, consistent with diatonic Western scales.
SCALE_PATTERNS: dict[str, list[int]] = {
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "natural_minor":  [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],   # raised 7th
    "dorian":         [0, 2, 3, 5, 7, 9, 10],   # minor with raised 6th
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],   # major with flat 7th
}

# Maps chord quality names to scale-degree *indices* (0-based) that form
# the chord.  Indices wrap around the 7-note scale with modulo arithmetic.
#
#   "triad"   → root, 3rd, 5th      (3 notes)
#   "seventh" → root, 3rd, 5th, 7th (4 notes)
CHORD_TYPES: dict[str, list[int]] = {
    "triad":   [0, 2, 4],
    "seventh": [0, 2, 4, 6],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_scale(root_name: str, scale_type: str) -> list[int]:
    """Return the pitch classes (0-11) for a given key and scale type.

    Args:
        root_name:  Root note name, e.g. ``"D"``, ``"Bb"``, ``"F#"``.
        scale_type: One of the keys in ``SCALE_PATTERNS``.

    Returns:
        A list of 7 pitch classes representing the scale degrees,
        starting from the root.

    Example::

        >>> build_scale("D", "harmonic_minor")
        [2, 4, 5, 7, 9, 10, 1]
    """
    root_pc = NOTE_TO_PC[root_name]
    pattern = SCALE_PATTERNS[scale_type]
    return [(root_pc + step) % 12 for step in pattern]


def chord_from_scale(
    scale: list[int],
    degree: int,
    chord_type: str
) -> list[int]:
    """Build a chord by stacking scale degrees on top of a root degree.

    Args:
        scale:      7 pitch classes as returned by ``build_scale``.
        degree:     0-based index of the chord root within the scale.
        chord_type: One of the keys in ``CHORD_TYPES`` (``"triad"`` or
                    ``"seventh"``).

    Returns:
        A list of pitch classes (0-11) belonging to the chord.

    Example::

        >>> scale = build_scale("C", "major")   # [0,2,4,5,7,9,11]
        >>> chord_from_scale(scale, 0, "triad") # I triad
        [0, 4, 7]  # C, E, G
    """
    indices = CHORD_TYPES[chord_type]
    return [scale[(degree + i) % len(scale)] for i in indices]


def pcs_to_midi_in_range(
    pcs: list[int],
    low: int = 36,
    high: int = 60
) -> list[int]:
    """Convert pitch classes to MIDI note numbers within a given range.

    Iterates over octaves 1-6 and collects every MIDI note whose pitch
    class is in ``pcs`` and whose value falls within [``low``, ``high``].

    Args:
        pcs:  Pitch classes (0-11) to materialise into MIDI notes.
        low:  Minimum MIDI note (inclusive).  Default: 36 (C2).
        high: Maximum MIDI note (inclusive).  Default: 60 (C4).

    Returns:
        Sorted list of MIDI note numbers matching the pitch classes
        within the requested range.
    """
    midi_notes = []
    for octave in range(1, 7):
        for pc in pcs:
            note = pc + 12 * octave
            if low <= note <= high:
                midi_notes.append(note)
    return midi_notes


def get_chord_midi_notes(
    root_name: str,
    scale_type: str,
    degree: int,
    chord_type: str
) -> list[int]:
    """High-level helper: return MIDI notes for a chord in a given key.

    Combines ``build_scale``, ``chord_from_scale``, and
    ``pcs_to_midi_in_range`` into a single convenience call.

    Args:
        root_name:  Key centre, e.g. ``"D"``.
        scale_type: Scale/mode name, e.g. ``"harmonic_minor"``.
        degree:     0-based chord degree within the scale (0 = tonic).
        chord_type: Chord quality: ``"triad"`` or ``"seventh"``.

    Returns:
        MIDI note numbers (bass range, C2–C4) belonging to the chord.

    Example::

        >>> get_chord_midi_notes("C", "major", 1, "triad")
        [38, 41, 45, 50, 53, 57]   # D-minor triad across two octaves
    """
    scale      = build_scale(root_name, scale_type)
    chord_pcs  = chord_from_scale(scale, degree, chord_type)
    return pcs_to_midi_in_range(chord_pcs)
