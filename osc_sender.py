"""
osc_sender.py
=============
OSC message sender for BassGen.

Wraps ``pythonosc.SimpleUDPClient`` to provide a typed, single-purpose
interface for sending bass-note events to Pure Data.

The OSC message format sent to Pure Data
-----------------------------------------
Address : ``/bass/note``
Arguments (in order):

    pitch     (int)   MIDI note number (0-127)
    duration  (float) Note duration in seconds
    velocity  (int)   MIDI velocity (1-127)
    beat_pos  (int)   16th-note step within the bar (0-15)

Pure Data receives these four values as a list and routes them to the
appropriate objects (e.g. ``noteout``, envelope, etc.).
"""

from pythonosc.udp_client import SimpleUDPClient


class OSCSender:
    """UDP-based OSC client for sending bass note events to Pure Data.

    Args:
        ip:   Destination IP address.  Use ``"127.0.0.1"`` for a local PD
              patch (default).
        port: Destination UDP port that Pure Data is listening on
              (default: 8000).

    Example::

        sender = OSCSender()
        sender.send_note(pitch=38, duration=0.12, velocity=100, beat_pos=0)
    """

    def __init__(self, ip: str = "127.0.0.1", port: int = 8000) -> None:
        self.client = SimpleUDPClient(ip, port)

    def send_note(
        self,
        pitch: int,
        duration: float,
        velocity: int,
        beat_pos: int
    ) -> None:
        """Send a single bass note event over OSC.

        Args:
            pitch:    MIDI note number (e.g. 38 = D2).
            duration: Note-on duration in seconds.  Pure Data uses this
                      to schedule the note-off message.
            velocity: MIDI velocity 1-127.  Values are expected to be
                      pre-clamped by the caller.
            beat_pos: 16th-note step index within the current bar (0-15).
                      Sent for diagnostic / visualisation purposes in PD.
        """
        self.client.send_message(
            "/bass/note",
            [pitch, duration, velocity, beat_pos]
        )
