"""Record a Surf Daddy show from report.json as report.mp3, with caption timings.
Usage: python build_show.py <show folder containing report.json>
Script tokens: [BARK] = Gus barks.  [SNACK] = Gus barks, a treat drops on a string and he crunches it.
The voice model (kokoro.onnx, voices.bin) is read from the show folder if present, else from this script's folder.
"""
import json, os, re, shutil, subprocess, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, lfilter
from kokoro_onnx import Kokoro

VOICE, SPEED, GAP, SR = "am_michael", 0.9, 0.28, 24000

def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)

def gus_bark():
    rng = np.random.default_rng(3)
    def one(dur, f0, f1):
        n = int(dur * SR); t = np.arange(n) / SR
        f = f0 * (f1 / f0) ** (t / dur) * (1 + 0.08 * np.sin(2 * np.pi * 35 * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = (sum((1 / k ** 0.9) * np.sin(k * ph) for k in range(1, 25)) + 0.6 * rng.standard_normal(n))
        x *= np.minimum(1, t / 0.012) * np.exp(-t / 0.07)
        y = bp(x, 400, 1100) + 0.7 * bp(x, 1300, 2600) + 0.25 * bp(x, 2800, 4200)
        y = np.tanh(2.5 * y / np.max(np.abs(y)))
        return y / np.max(np.abs(y)) * 0.85
    return np.concatenate([one(0.2, 560, 330), np.zeros(int(0.11 * SR)), one(0.24, 600, 320)]).astype(np.float32)

def gus_snack():
    """Bark, a short pause while the treat drops, then four crunches."""
    rng = np.random.default_rng(11)
    def crunch():
        n = int(0.11 * SR); t = np.arange(n) / SR
        x = rng.standard_normal(n) * (np.exp(-t / 0.025) + 0.5 * np.exp(-np.maximum(t - 0.035, 0) / 0.02) * (t > 0.035))
        y = bp(x, 1800, 6500) + 0.4 * bp(x, 500, 1500)
        return (y / np.max(np.abs(y)) * 0.6).astype(np.float32)
    parts = [gus_bark(), np.zeros(int(0.45 * SR), dtype=np.float32)]
    for g in (0.17, 0.2, 0.16, 0.0):
        parts += [crunch(), np.zeros(int(g * SR), dtype=np.float32)]
    return np.concatenate(parts).astype(np.float32)

d = sys.argv[1] if len(sys.argv) > 1 else "."
here = os.path.dirname(os.path.abspath(__file__))
model_dir = d if os.path.exists(os.path.join(d, "kokoro.onnx")) else here
rp = os.path.join(d, "report.json")
r = json.load(open(rp))
k = Kokoro(os.path.join(model_dir, "kokoro.onnx"), os.path.join(model_dir, "voices.bin"))
SENT = r"[^.!?]+[.!?]+[\"')\]]*|\S[^.!?]*$"

chunks, caps, t = [], [], 0.0
def add(a, text, speaker="surf"):
    global t
    dur = len(a) / SR
    caps.append({"start": round(t, 2), "end": round(t + dur, 2), "text": text, "speaker": speaker})
    chunks.extend([a.astype(np.float32), np.zeros(int(GAP * SR), dtype=np.float32)])
    t += dur + GAP

source = r.get("script_source") or r.get("script", "")
for part in re.split(r"(\[BARK\]|\[SNACK\])", source):
    if part == "[BARK]":
        add(gus_bark(), "Woof! Woof!", "gus")
    elif part == "[SNACK]":
        add(gus_snack(), "Woof! Crunch, crunch, crunch.", "snack")
    else:
        for line in [s.strip() for s in re.findall(SENT, part) if s.strip()]:
            a, _ = k.create(line, voice=VOICE, speed=SPEED, lang="en-us")
            add(a, line)

audio = np.concatenate(chunks) if chunks else np.zeros(SR, dtype=np.float32)
wav = os.path.join(d, "report.wav")
sf.write(wav, audio, SR)
out = "report.wav"
if shutil.which("ffmpeg"):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-b:a", "96k", os.path.join(d, "report.mp3")], check=True)
    out = "report.mp3"
    os.remove(wav)
r["script_source"] = source
r["script"] = re.sub(r"\s{2,}", " ", re.sub(r"\[(BARK|SNACK)\]", "", source)).strip()
r.pop("needs_recording", None)
r["audio"] = out
r["captions"] = caps
json.dump(r, open(rp, "w"), indent=1, ensure_ascii=False)
print(f"{out}: {t:.1f}s, {len(caps)} captions")
