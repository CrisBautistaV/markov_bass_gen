"""
osc_receiver.py
===============
OSC message receiver for BassGen.

This module exposes a ``pythonosc`` Dispatcher that listens for control
messages arriving from Pure Data (or any OSC-capable host) and stores the
incoming values in module-level state variables.

Architecture note
-----------------
State is kept in plain module globals for simplicity.  Each handler
validates and stores its value; the main loop in the notebook reads the
globals on each tick.  This single-writer / single-reader model is safe
for the current architecture because:

  * The OSC server runs in a daemon thread (one writer per variable).
  * The main loop reads each variable once per step (one reader).

If the system is later extended to multiple handlers or faster tempos,
consider replacing the globals with a threading.Lock-protected state
object or a thread-safe queue.

OSC address map
---------------
+---------------------------+-------------------------------------------+
| Address                   | Effect                                    |
+===========================+===========================================+
| /bass/enable   <int>      | 0 = mute generator, 1 = activate         |
| /bass/degree   <int>      | Schedule chord degree change (1-based)    |
| /bass/rhythm   <str>      | Schedule rhythm pattern change by name    |
| /bass/key      <str>      | Schedule key (root note) change           |
| /bass/keyType  <str>      | Schedule scale/mode change                |
| /transport/tempo  <float> | Update BPM in real time                   |
| /transport/start          | Reset step counter and start transport    |
| /transport/stop           | Mark transport as stopped                 |
+---------------------------+-------------------------------------------+

"Pending" vs "current" state
-----------------------------
Parameters marked ``pending_*`` are not applied immediately.  The main
loop applies them only at step 0 (bar boundary) so that changes are
always bar-aligned and never cause mid-bar glitches.
"""

from pythonosc.dispatcher import Dispatcher


# ---------------------------------------------------------------------------
# State variables
# ---------------------------------------------------------------------------

# Whether the bass generator should produce notes.
bass_enabled: bool = False

# Chord degree to apply at the next bar boundary (1-based from PD, stored
# as-is and converted to 0-based in the main loop).
pending_degree: int | None = None

# Rhythm pattern name to apply at the next bar boundary.
pending_rhythm: str | None = "habanera"

# Key root note (e.g. "D", "Bb") to apply at the next bar boundary.
pending_key: str | None = "D"

# Scale/mode type (e.g. "major", "harmonic_minor") to apply at the next
# bar boundary.
pending_keyType: str | None = "major"

# Current tempo in BPM, updated in real time (not bar-aligned).
bpm: float = 120.0

# Current 16th-note step within the bar (0-15).  Set to -1 until the
# first /transport/start message is received.
step: int = -1

# Whether Pure Data's transport is currently running.
transport_running: bool = False


# ---------------------------------------------------------------------------
# OSC handler functions
# ---------------------------------------------------------------------------

def handle_bass_enable(address: str, value: int) -> None:
    """Toggle the bass generator on or off.

    Args:
        address: OSC address (``/bass/enable``).
        value:   Non-zero = enabled, 0 = muted.
    """
    global bass_enabled
    bass_enabled = bool(value)
    print(f"[OSC] bass_enabled = {bass_enabled}")


def handle_bass_degree(address: str, value: int) -> None:
    """Schedule a chord-degree change at the next bar boundary.

    Pure Data sends 1-based degrees (1 = tonic).  The value is stored
    as-is; the main loop subtracts 1 when it applies the change.

    Args:
        address: OSC address (``/bass/degree``).
        value:   Chord degree, 1-based integer.
    """
    global pending_degree
    pending_degree = int(value)
    print(f"[OSC] next_degree = {pending_degree}")


def handle_tempo(address: str, value: float) -> None:
    """Update the playback tempo.

    This change takes effect immediately (not bar-aligned) so the step
    duration adjusts on the next tick.

    Args:
        address: OSC address (``/transport/tempo``).
        value:   Tempo in BPM.
    """
    global bpm
    bpm = float(value)
    print(f"[OSC] tempo = {bpm}")


def handle_transport_start(address: str) -> None:
    """Reset the step counter and mark transport as running.

    Called when Pure Data's transport starts or loops.  Resets
    ``step`` to 0 so the Python loop stays bar-aligned with PD.

    Args:
        address: OSC address (``/transport/start``).
    """
    global step, transport_running
    if not transport_running:
        step = 0
        transport_running = True


def handle_transport_stop(address: str) -> None:
    """Mark transport as stopped.

    Args:
        address: OSC address (``/transport/stop``).
    """
    global transport_running
    transport_running = False


def handle_bass_rhythm(address: str, value: str) -> None:
    """Schedule a rhythm pattern change at the next bar boundary.

    Args:
        address: OSC address (``/bass/rhythm``).
        value:   Pattern name (must be a key in ``rhythm.RHYTHM_PATTERNS``).
    """
    global pending_rhythm
    pending_rhythm = value
    print(f"[OSC] next_rhythm = {pending_rhythm}")


def handle_bass_key(address: str, value: str) -> None:
    """Schedule a key (root note) change at the next bar boundary.

    Args:
        address: OSC address (``/bass/key``).
        value:   Root note name, e.g. ``"D"``, ``"Bb"``.
    """
    global pending_key
    pending_key = value
    print(f"[OSC] next_key = {pending_key}")


def handle_bass_keyType(address: str, value: str) -> None:
    """Schedule a scale/mode change at the next bar boundary.

    Args:
        address: OSC address (``/bass/keyType``).
        value:   Scale name, e.g. ``"major"``, ``"harmonic_minor"``.
    """
    global pending_keyType
    pending_keyType = value
    print(f"[OSC] next_keyType = {pending_keyType}")


# ---------------------------------------------------------------------------
# Dispatcher registration
# ---------------------------------------------------------------------------

dispatcher = Dispatcher()
dispatcher.map("/bass/enable",      handle_bass_enable)
dispatcher.map("/bass/degree",      handle_bass_degree)
dispatcher.map("/bass/rhythm",      handle_bass_rhythm)
dispatcher.map("/bass/key",         handle_bass_key)
dispatcher.map("/bass/keyType",     handle_bass_keyType)
dispatcher.map("/transport/tempo",  handle_tempo)
dispatcher.map("/transport/start",  handle_transport_start)
dispatcher.map("/transport/stop",   handle_transport_stop)
