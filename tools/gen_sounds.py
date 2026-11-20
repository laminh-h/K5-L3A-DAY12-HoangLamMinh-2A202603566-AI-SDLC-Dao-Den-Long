"""Generate all game sounds procedurally (stdlib only) -> lantern/assets/sounds/*.wav.
Self-made, released with the project under its LICENSE (see CREDITS.md).
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "lantern", "assets", "sounds")


def write(name, samples):
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


def tone(freqs, dur, vol=0.5, attack=0.01, decay=None, wave_="sine"):
    n = int(RATE * dur)
    decay = dur if decay is None else decay
    out = []
    for i in range(n):
        t = i / RATE
        f = freqs[0] + (freqs[-1] - freqs[0]) * (t / dur)
        ph = 2 * math.pi * f * t
        v = math.sin(ph) if wave_ == "sine" else (2 / math.pi) * math.asin(math.sin(ph))
        env = min(1.0, t / attack) * math.exp(-3 * t / decay)
        out.append(v * env * vol)
    return out


def mix(*parts):
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def noise(dur, vol=0.3, seed=1):
    r = random.Random(seed)
    n = int(RATE * dur)
    return [r.uniform(-1, 1) * vol * math.exp(-4 * i / n) for i in range(n)]


def main():
    write("pickup", tone([880, 1320], 0.15, 0.4))
    write("light", mix(tone([523], 0.9, 0.3), tone([659], 0.9, 0.25), tone([784], 0.9, 0.2)))
    write("pulse", mix(tone([300, 900], 0.5, 0.4, wave_="tri"), noise(0.4, 0.1, 2)))
    write("hit", mix(tone([220, 110], 0.35, 0.5, wave_="tri"), noise(0.25, 0.25, 3)))
    write("jump", tone([400, 700], 0.18, 0.35))
    write("dash", noise(0.22, 0.4, 4))
    write("win", sum((tone([f], 0.35, 0.3) for f in (523, 659, 784, 1046)), []))
    write("lose", sum((tone([f], 0.4, 0.3, wave_="tri") for f in (392, 330, 262)), []))
    write("shade", tone([180, 120], 0.6, 0.35, wave_="tri"))
    write("tick", tone([1000], 0.06, 0.3))
    write("wind", noise(1.2, 0.25, 5))
    write("refuel", tone([660, 990], 0.25, 0.3))
    # night ambience: slow pentatonic arpeggio over a pad, loops in 8 s
    notes = [262, 294, 330, 392, 440, 392, 330, 294]
    melody = sum((tone([f * 2], 1.0, 0.12, attack=0.2, decay=0.9) for f in notes), [])
    pad = [0.06 * math.sin(2 * math.pi * 131 * i / RATE) * (0.6 + 0.4 * math.sin(2 * math.pi * i / (RATE * 8)))
           for i in range(RATE * 8)]
    write("music", mix(melody, pad))


if __name__ == "__main__":
    main()
