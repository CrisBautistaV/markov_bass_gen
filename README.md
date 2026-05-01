# BassGen 🎸

**A Markov chain bass line generator bridging Python and Pure Data via OSC**

BassGen generates harmonically aware, rhythmically varied bass lines in real time. A Python engine handles music theory and stochastic generation; Pure Data handles audio synthesis and transport. They communicate over OSC (Open Sound Control), so tempo, key, scale, chord degree, and rhythm pattern can all be changed live from the PD patch while the generator keeps playing.

---

## How it works

```
┌─────────────────────────────────────────────────────────┐
│                   autoBass.pd  (main patch)             │
│                                                         │
│  mymetro  →  tempo, bar sync, step counter              │
│  UI controls → key, scale, degree, rhythm, enable       │
│                        │                                │
│               autobassc.pd  (OSC sender)                │
│         formats and sends all control messages          │
└────────────────────────┬────────────────────────────────┘
                         │  UDP :9000
                         │  /transport/tempo  /transport/start
                         │  /bass/enable  /bass/degree
                         │  /bass/key  /bass/keyType  /bass/rhythm
                         ▼
              osc_receiver.py  →  pending state
                         │        (applied at bar boundary)
                         ▼
          BassGen_Python-Pd.ipynb  (main loop)
            ├─ rhythm.py      →  which steps fire, at what velocity
            ├─ pitch.py       →  which MIDI notes are valid
            └─ markovgen.py   →  which note to play next
                         │
                         │  UDP :8000
                         │  /bass/note [pitch, duration, velocity, step]
                         ▼
┌─────────────────────────────────────────────────────────┐
│               autobassi.pd  (audio engine)              │
│                                                         │
│  oscparse → unpack → mtof → tabosc4~ (basswave table)  │
│  vline~ envelope shaped by duration + velocity          │
│  audio out → dac~                                       │
└─────────────────────────────────────────────────────────┘
```

### Rhythm engine (`rhythm.py`)
Defines 16-step (4/4) patterns where each cell is a velocity weight (0 = rest, 1.0 = full accent). Pattern changes sent via OSC are applied only at bar boundaries (step 0) to avoid mid-bar glitches.

### Harmonic context (`pitch.py`)
Converts a key + scale type + chord degree + chord quality into concrete MIDI notes in the bass range (C2–C4). Chord tones are distinguished from scale tones so the Markov engine can apply different acceptance rules on strong vs. weak beats.

### Markov pitch engine (`markovgen.py`)
Drives melodic motion using a first-order Markov chain over *intervals* (semitones of movement) rather than absolute pitches, so the same transition table works in any key. The chain prefers stepwise motion and strongly resolves back by step after any large leap. Harmonic acceptance acts as a rejection-sampling filter.

### OSC layer (`osc_sender.py`, `osc_receiver.py`)
`OSCSender` wraps `pythonosc.SimpleUDPClient` to send `/bass/note` to PD. `osc_receiver.py` runs a `ThreadingOSCUDPServer` in a daemon thread and exposes module-level state variables polled by the main loop each tick.

---

## Pure Data patches

The project includes four `.pd` files. Three are abstractions (reusable sub-patches) and one is the top-level patch you open to run the system.

### `autoBass.pd` — main patch *(open this one)*

The top-level patch. On load it automatically connects to Python via `loadbang → connect 127.0.0.1 9000`. It contains:

- **Transport section** — `mymetro` abstraction driven by a toggle and a BPM slider (range 10–200, default 100). A `sel 3` object fires a "pre-bar" signal one step before each bar boundary, giving Python advance notice to prepare the next bar's parameters.
- **Key / scale controls** — message boxes for root notes (`D`, `E`, …) and scale types (`major`, `harmonic_minor`).
- **Degree controls** — message boxes for chord degrees 1–5 wired into `autobassc`.
- **Rhythm controls** — message boxes for `habanera`, `eighths`, `quarters`, `walking`.
- **Enable toggle** — arms the generator; no notes are sent until this is on.
- **Audio** — receives the audio signal from `autobassi` and routes it to `dac~`.

### `autobassc.pd` — OSC control sender (abstraction)

Formats and sends all outgoing OSC messages to Python over UDP port 9000. Every control parameter in `autoBass.pd` is routed through this abstraction. It uses `iemnet/udpsend` and `oscformat` to build properly addressed OSC packets.

| Inlet | Sends OSC address |
|---|---|
| tempo | `/transport/tempo` |
| bar start | `/transport/start` |
| pre-bar | `/transport/stop` |
| enable | `/bass/enable` |
| key | `/bass/key` |
| key type | `/bass/keyType` |
| degree | `/bass/degree` |
| rhythm | `/bass/rhythm` |

> **Dependency:** requires the `iemnet` external. Install via Deken: `Help → Find externals → iemnet`.

### `autobassi.pd` — audio instrument (abstraction)

Receives `/bass/note` OSC messages from Python (UDP port 8000) and synthesises the audio. Signal flow:

```
oscparse → list trim → route bass → route note
  → unpack [pitch, duration, velocity, beat_pos]
  → mtof (MIDI → Hz)
  → tabosc4~ basswave  (wavetable oscillator)
  → vline~ envelope  (duration ms, velocity / 127)
  → *~ → outlet~
```

The `basswave` table is a 515-sample custom waveform stored directly in the patch — a warm bass-voiced shape with a slow attack and rolled-off harmonics. Four message boxes let you swap the waveform in real time:

| Message | Waveform |
|---|---|
| `basswave const 0` | Silence / reset |
| `basswave sinesum 256 1 0.5 0.25` | Warm additive (fundamental + 2 harmonics) |
| `basswave sinesum 512 1 1 1 1` | Saturated / full harmonics |
| `basswave cosinesum 512 0 1` | Cosine (bright, percussive) |

### `mymetro.pd` — sync metronome (abstraction)

A configurable metronome that drives all timing in the system. Accepts three inlets (enable, subdivision, tempo in BPM) and produces five outlets:

| Outlet | Signal |
|---|---|
| beat flag | bangs on every beat |
| half tempo | bangs at half the beat rate |
| bar begin | bangs on beat 1 of each bar |
| beat count | counter 0–3 within each bar |
| bar count | total bars elapsed |

Internally it computes the 16th-note period as `60000 / tempo / subdivision`, runs a `metro`, and uses `mod 4` counters to derive beat and bar signals.

---

## Project structure

```
BassGen/
├── autoBass.pd                 # Main patch — open this in Pure Data
├── autobassc.pd                # Abstraction: OSC control sender → Python (:9000)
├── autobassi.pd                # Abstraction: OSC note receiver + audio synth
├── mymetro.pd                  # Abstraction: sync metronome
├── BassGen_Python-Pd.ipynb     # Main notebook: setup, main loop, test cells
├── markovgen.py                # Markov interval chain + harmonic filter
├── pitch.py                    # Music theory utilities (scales, chords, MIDI)
├── rhythm.py                   # Rhythm pattern library + random selection
├── osc_sender.py               # OSC client → Pure Data (:8000)
├── osc_receiver.py             # OSC server ← Pure Data (:9000)
└── README.md
```

---

## Requirements

### Python
```
python >= 3.10
python-osc
```
```bash
pip install python-osc
```
The notebook was developed with a `musicTech` conda environment (Python 3.13). The optional direct-MIDI test cell also requires `pygame`.

### Pure Data
- Pure Data Vanilla (or Pd-l2ork / Purr Data)
- **iemnet** external — install via Deken: `Help → Find externals → iemnet`

---

## Usage example

This walkthrough goes from a cold start to a live D harmonic minor bass line over a habanera rhythm at 113 BPM — the default configuration in the patches.

### 1 · Start the Python side

Open `BassGen_Python-Pd.ipynb` and run the cells in order.

**Imports cell** — loads all modules.

**Config cell** — defaults are fine: `PYTHON_LISTEN_PORT = 9000`.

**OSC server cell** — starts the listener thread:
```
OSC server listening on 127.0.0.1:9000
```

**Main loop cell** — set starting parameters and run:
```python
key            = 'D'
key_type       = 'harmonic_minor'
chord_type     = 'triad'
current_degree = 0
```
The loop is now running but silent — it waits for `/bass/enable 1` from PD.

### 2 · Open Pure Data

Open `autoBass.pd`. The `loadbang` fires immediately and sends:
```
connect 127.0.0.1 9000
```
`autobassc` is now connected to Python. No errors in the PD console means `iemnet` is installed correctly.

### 3 · Configure the sound

With the metro still **off**, click the message boxes in `autoBass.pd` to set your parameters:

| Click | Sends to Python |
|---|---|
| `symbol D` | `/bass/key  D` |
| `symbol harmonic_minor` | `/bass/keyType  harmonic_minor` |
| `1` (degree) | `/bass/degree  1` |
| `symbol habanera` | `/bass/rhythm  habanera` |

Python stores these as `pending_*` values — they will be applied at the first bar boundary (step 0).

### 4 · Start the metro

Turn on the enable toggle connected to `mymetro` and set the BPM slider to **113**.

`mymetro` begins ticking. On every bar start it sends:
```
/transport/tempo    113.0
/transport/start
```
Python logs:
```
[OSC] tempo = 113.0
```
The step counter resets to 0. All pending parameters are applied and the harmonic context is built:
```
Key: D harmonic_minor  |  scale PCs: [2, 4, 5, 7, 9, 10, 1]
Degree 0 chord MIDI notes: [38, 41, 45, 50, 53, 57]
```

### 5 · Enable the bass

Click the **bass enable toggle** in `autoBass.pd`. This sends:
```
/bass/enable   1
```
Python logs:
```
[OSC] bass_enabled = True
```
The generator is live. On each hit step of the habanera pattern, Python sends back:
```
/bass/note   [38, 0.132, 127, 0]     ←  D2,  bar downbeat    (step 0)
/bass/note   [41, 0.132,  38, 6]     ←  F2,  beat 2 offbeat  (step 6, ghost)
/bass/note   [38, 0.132, 127, 12]    ←  D2,  beat 3          (step 12)
```
`autobassi` receives each message, converts MIDI pitch to Hz via `mtof`, triggers the `tabosc4~` oscillator through a `vline~` amplitude envelope, and sends audio to `dac~`.

### 6 · Change parameters live

All changes are bar-aligned — PD sends them instantly, but Python applies them at the next step 0.

**Change to degree IV:**
Click `4` in the degree section.
```
[OSC] next_degree = 4
```
At the next bar the chord rebuilds as degree IV of D harmonic minor (G minor triad). The Markov engine continues from the last note, now filtered against the new chord tones.

**Change rhythm to walking:**
Click `symbol walking`.
```
[OSC] next_rhythm = walking
```
At the next bar, every 16th-note step fires at graduated velocities — a dense walking-bass texture.

**Change key to E major:**
Click `symbol E`, then `symbol major`.
```
[OSC] next_key = E
[OSC] next_keyType = major
```
At the next bar, the scale and chord rebuild in E major. The Markov engine carries on from the last note, now filtered against the new harmonic context.

### 7 · Stop

1. Turn off the bass enable toggle → `[OSC] bass_enabled = False`. Loop keeps running silently.
2. Turn off the metro toggle → `mymetro` stops ticking.
3. Stop the notebook kernel (■) → OSC server thread shuts down automatically.

---

## OSC reference

### Python receives (port 9000)

| Address | Type | Applied |
|---|---|---|
| `/bass/enable` | int 0/1 | Immediately |
| `/bass/degree` | int 1–7 | Next bar |
| `/bass/rhythm` | symbol | Next bar |
| `/bass/key` | symbol | Next bar |
| `/bass/keyType` | symbol | Next bar |
| `/transport/tempo` | float | Immediately |
| `/transport/start` | *(no args)* | Immediately — resets step counter |
| `/transport/stop` | *(no args)* | Immediately |

### Python sends (port 8000)

| Address | Arguments | Description |
|---|---|---|
| `/bass/note` | `int float int int` | pitch (MIDI), duration (s), velocity (1–127), step (0–15) |

---

## Configuration reference

### Available scales

| Name | Intervals from root |
|---|---|
| `major` | 0 2 4 5 7 9 11 |
| `natural_minor` | 0 2 3 5 7 8 10 |
| `harmonic_minor` | 0 2 3 5 7 8 11 (raised 7th) |
| `dorian` | 0 2 3 5 7 9 10 (minor + ♮6) |
| `mixolydian` | 0 2 4 5 7 9 10 (major + ♭7) |

### Available rhythm patterns (4/4)

| Name | Character |
|---|---|
| `quarters` | Four quarter notes per bar |
| `eighths` | Alternating quarters and eighths |
| `offbeat` | All upbeats — creates tension |
| `syncopated` | Displaced accents — funk/soul feel |
| `walking` | Every 16th note — busy texture |
| `sparse` | Downbeats only — open, minimal |
| `habanera` | Cuban habanera clave cell |

### Markov interval chain

The engine chooses how far to move (in semitones) from the last note. Key tendencies:

- After **staying still (0)**: equal chance of small steps in either direction.
- After a **small step**: prefers to continue or reverse — natural stepwise motion.
- After a **large leap (4th or 5th)**: strongly prefers to resolve back by step.

The harmonic filter then accepts or rejects each candidate:
- **Strong beats** (steps 0, 8): chord tones only.
- **Weak beats**: chord tones or scale tones.

---

## Roadmap / known limitations

- [ ] Start phrases on the tonic of the current chord (not always the lowest chord tone)
- [ ] Detect and avoid obvious parallel-octave motion between consecutive degree changes
- [ ] Expand the rhythm library: at least two variants per named pattern, each with its own probability weight
- [ ] Investigate edge cases where the Markov chain assigns the 0-interval a disproportionately high weight after rejection-sampling collisions
- [ ] Replace module-level globals in `osc_receiver.py` with a thread-safe state object if multiple OSC handlers are added or tempo increases significantly

---

## License

GPL v3 — see `LICENSE`.
