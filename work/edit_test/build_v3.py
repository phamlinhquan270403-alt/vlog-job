"""Edit test: Laurin Hwang "an UNEDITED day in my life" (CC BY) -> ~3.5 min vlog in the apinvy style
(docs/edit-recipe.md). Video segments are cut with ffmpeg; the whole audio (speech, music beds with ducking,
SFX) is mixed in numpy; text overlays are PNGs made with Pillow and composited in one final ffmpeg pass.

usage: py work/edit_test/build.py v1     -> work/edit_test/renders/v1.mp4 + v1.srt
"""
import json, os, re, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "reference", "youtube", "MPZWJls31Vw", "video.mp4")
MUSIC = os.path.join(HERE, "music")
W, H, FPS, SR = 1280, 720, 30, 48000
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v1"
TMP = os.path.join(HERE, "tmp")
OUT = os.path.join(HERE, "renders")
for d in (TMP, OUT, os.path.join(TMP, "seg"), os.path.join(TMP, "png")):
    os.makedirs(d, exist_ok=True)
FONTS = "C:/Windows/Fonts/"

# ---------------------------------------------------------------- transcript lookup
# Whisper word timings [start, word, end] (YouTube auto-caption times were too loose and clipped words in v1 drafts)
WORDS = json.load(open(os.path.join(HERE, "words_whisper.json")))
NORM = [re.sub(r"[^a-z0-9']", "", w[1].lower()) for w in WORDS]


def find(phrase, after=0.0, full=False):
    """(start, end) of a phrase from Whisper word timings.
    full=True also returns (previous word's end, next word's start) to bound the cut search."""
    toks = [re.sub(r"[^a-z0-9']", "", t) for t in phrase.lower().split()]
    for i in range(len(WORDS)):
        if WORDS[i][0] < after - 0.5:
            continue
        if NORM[i:i + len(toks)] == toks:
            j = i + len(toks)
            prev_end = WORDS[i - 1][2] if i else 0.0
            nxt = WORDS[j][0] if j < len(WORDS) else WORDS[j - 1][2] + 1.0
            res = (WORDS[i][0], WORDS[j - 1][2])
            return res + (prev_end, nxt) if full else res
    near = " ".join(w[1] for w in WORDS if after <= w[0] < after + 25)
    raise SystemExit(f"phrase not found after {after}: {phrase!r}\n  text there: {near}")


def _load_src_audio():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


SRC_AUDIO = _load_src_audio()
_E = np.abs(SRC_AUDIO).max(axis=1)
_HOP = SR // 100  # 10 ms energy frames
_RMS = np.sqrt(np.convolve(_E[: len(_E) // _HOP * _HOP].reshape(-1, _HOP).mean(axis=1) ** 2,
                           np.ones(3) / 3, mode="same"))


def snap(t, lo, hi):
    """Move a cut to the quietest 10 ms frame within [t+lo, t+hi]: caption word times are approximate,
    so cutting exactly on them clips words."""
    i0, i1 = max(0, int((t + lo) * 100)), min(len(_RMS) - 1, int((t + hi) * 100))
    if i1 <= i0:
        return t
    return (i0 + int(np.argmin(_RMS[i0:i1 + 1]))) / 100


def span(first, last, after=0.0, pre=0.12, post=0.0):
    a, _, prev_end, _ = find(first, after, full=True)
    _, b, _, nxt = find(last, a, full=True)
    # start: quietest point in the gap between the previous word's end and the first word's start
    lo = max(prev_end + 0.02, a - pre - 0.3)  # never pick up the previous word's tail
    a = min(snap(lo, 0, max(0.0, a - 0.04 - lo)), a - 0.08)  # always start before the first word's onset
    # end: quietest point in the gap between the last word's end and the next word's start (post extends the hold)
    last_end = b
    if nxt - last_end < 0.25:   # connected speech: cut in the energy valley between the two words
        b = snap(last_end - 0.12, 0, (nxt + 0.05) - (last_end - 0.12))
    else:                       # a real pause: hold >= 0.15 s, end in the quietest spot of the pause
        hi = min(nxt - 0.06, last_end + 0.6 + post)
        b = snap(last_end + 0.15, 0, max(0.0, hi - last_end - 0.15)) + (post if nxt - last_end > post + 0.4 else 0)
    return round(a, 2), round(b, 2)


# ---------------------------------------------------------------- edit decision list
EDL = []   # dicts: v=(in,out), audio: "src"|"mute", gain, zoom, name


def seg(v, audio="src", gain=1.0, zoom=1.0, name=None, vo=False, vsrc=None):
    # vo=True: her voice over footage (no lip-sync), so the picture may skip flicker shots and run on
    EDL.append({"v": v, "audio": audio, "gain": gain, "zoom": zoom, "name": name, "vo": vo, "vsrc": vsrc})


def talk(first, last, after=0.0, zoom=1.0, name=None, pre=0.12, post=0.0, vo=False, vsrc=None):
    seg(span(first, last, after, pre, post), zoom=zoom, name=name, vo=vo, vsrc=vsrc)


def broll(t, dur, gain=0.0, zoom=1.0, name=None):
    # b-roll is always muted: the source has car-radio songs under several of these shots (v1 QA: "good 4 u")
    seg((t, round(t + dur, 2)), audio="mute", gain=0.0, zoom=zoom, name=name)


# 1. Cold open: 12 shots on the beat (2 beats @120 bpm = 1.0s), music only, script title on top
for i, t in enumerate([1.6, 3.2, 8.4, 178.8, 319.1, 327.6, 280.0, 291.0, 431.4, 442.0, 484.0, 515.5]):
    broll(t, 1.0, name="open" if i == 0 else None)

# 2. Intro, talking in the car (jump cuts)
talk("good morning guys", "day in my life", 15, name="intro")
talk("most of the time", "really aesthetic", 30)
talk("my life isn't perfect", "with you guys", 45)
talk("by unedited i mean", "wherever it's needed", 80, name="irony")
talk("so today is january", "go work out", 110)
seg((span("i'm gonna be late", "so let's", 150)[0], 162.5))  # runs on into the drink shot: Whisper misplaced "go"

# 3. Workout + drive
seg((162.5, 166.8), name="gym")  # "favorite caffeinated drink" (Whisper missed it; fixed shot times)
broll(170.6, 1.3, gain=0.15, name="drive")
broll(173.4, 1.3, gain=0.15)
broll(177.1, 1.3, gain=0.15)
broll(183.2, 1.4, gain=0.15)
talk("i just finished the workout", "when i work out", 185, name="red", zoom=1.1)
talk("i'm going to fullerton", "where i live", 195)
talk("and it's currently", "dermatologist appointment", 205)  # skips the run-on "at 11. my appointment's at 11"

# 4. Dermatologist
talk("i've had acne since", "middle school", 215, name="derm")
talk("and it always gets fixed", "slowly gets worse", 228)
talk("so they told me", "hurt as badly", 250, name="laser", vo=True, zoom=1.06)  # slow push: static tripod shots read as frozen  # its video passes the FULLERTON sign at ~+2s
talk("and this machine is the", "that they used", 262, zoom=1.05)
talk("and i know i look like", "an actual egg", 268, zoom=1.2, name="egg", post=0.4)
talk("and then after that", "final step", 275)
talk("my face was so purple", "i was suffocating", 284, vo=True, vsrc=290.35)  # picture: her post-laser face, one clean shot
talk("i literally look so scary", "kind of crazy", 290, zoom=1.15)
talk("so it looks like i murdered", "wash my face", 298, zoom=1.2, name="murder", post=0.3)

# 5. Crumbl
talk("now we're gonna get", "store like this", 305, name="crumbl_talk")
broll(319.1, 1.1, name="crumbl")  # after the 0.3 s whip shots (flashed in v1)
broll(322.0, 1.4, gain=0.2)
broll(325.0, 1.1, gain=0.2)
talk("oh the frosting's falling", "that one", 325)
talk("oh my god they look so good", "they look so good", 333)
talk("classic sugar cookie", "and neapolitan", 335)
talk("i didn't actually film me", "like bonding", 355, name="bonding", post=0.25)
talk("and i ate too much", "my stomach hurts now", 370, zoom=1.2, name="stomach")

# 6. Library
talk("now i'm on the way", "paying for them", 374, name="library_talk")
broll(389.8, 1.6, name="library")  # muted: car radio in the source here
broll(431.3, 1.2, gain=0.2)
broll(433.63, 1.3)  # ends exactly where the books take starts: one continuous shot
talk("i got quite a few books", "my favorite genre", 430, name="books")  # one take: v2 cut her off at "The wedding..."
talk("one of my new year's", "three or four books", 450, name="goal")

# 7. Home: packages + current book (stop before the song in the room starts)
talk("we're opening some packages", "leather pants", 470, name="home")
talk("show the camera", "show the camera", 480, zoom=1.2, post=0.5)
talk("i have got jim shark", "sports bra cute", 482)
talk("this is a book i'm currently", "so close to finishing", 488)

# 8. Ending: b-roll under her closing words (L-cut), soft piano, fade to black
broll(512.2, 2.4, name="ending")
broll(514.9, 3.4)
broll(329.8, 4.2)
VO = [("ending", 0.3, span("i didn't film anything", "no one's life is perfect", 515)[0],
       span("i didn't film anything", "no one's life is perfect", 515)[1] + 0.3, 1.0)]

# Two talk segments that overlap in the source (snapping pushed one past the other) would repeat audio:
# put their shared boundary at the quietest point of the overlap instead.
for s1, s2 in zip(EDL, EDL[1:]):
    if s1["audio"] == s2["audio"] == "src" and s1["v"][0] < s2["v"][0] < s1["v"][1]:
        cut = snap(s2["v"][0], 0, s1["v"][1] - s2["v"][0])
        s1["v"], s2["v"] = (s1["v"][0], round(cut, 2)), (round(cut, 2), s2["v"][1])

# Source cuts (Laurin's own trims). A talk segment whose head/tail reaches across one of them through near
# silence is trimmed to the cut, audio included: what is dropped is only pause, and no sliver is left.
_cuts_path = os.path.join(TMP, "src_cuts.json")
if not os.path.exists(_cuts_path):
    _err = subprocess.run(["ffmpeg", "-hide_banner", "-i", SRC, "-an", "-vf", r"scale=320:-2,select=gt(scene\,0.25),showinfo",
                           "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
    json.dump([float(m) for m in re.findall(r"pts_time:([\d.]+)", _err)], open(_cuts_path, "w"))
_CUTS = json.load(open(_cuts_path))


def _rms(a, b):
    x = SRC_AUDIO[int(a * SR):int(b * SR)]
    return float(np.sqrt((x ** 2).mean())) if len(x) else 0.0


for s in EDL:
    v0, v1 = s["v"]
    if s["audio"] == "src":
        def _no_word(x, y):
            return not any(w[0] < y - 0.03 and w[2] > x + 0.03 for w in WORDS)
        head = [c for c in _CUTS if v0 < c <= v0 + 0.6 and _rms(v0, c) < 0.035 and _no_word(v0, c)]
        tail = [c for c in _CUTS if v1 - 0.6 <= c < v1 and _rms(c, v1) < 0.035 and _no_word(c, v1)]
        s["v"] = (round(max(head), 3) if head else v0, round(min(tail), 3) if tail else v1)

# ---------------------------------------------------------------- timeline
t = 0.0
for s in EDL:
    s["dur"] = round(s["v"][1] - s["v"][0], 3)
    s["t"] = round(t, 3)
    t += s["dur"]
TOTAL = round(t, 3)
AT = {s["name"]: s for s in EDL if s["name"]}


def at(name, off=0.0):
    return AT[name]["t"] + off


def seg_end(name):
    return AT[name]["t"] + AT[name]["dur"]


def end_of(name):
    """Timeline time where the run of segments starting at `name` ends (= next named segment's start)."""
    i = EDL.index(AT[name])
    for s in EDL[i + 1:]:
        if s["name"]:
            return s["t"]
    return TOTAL


# ---------------------------------------------------------------- text overlays (PNG, full frame)
def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def png(name, draw_fn):
    path = os.path.join(TMP, "png", name + ".png")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(txt))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(txt.getchannel("A").point(lambda a: int(a * 0.55)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(shadow, (2, 2))
    img.alpha_composite(txt)
    img.save(path)
    return path


WHITE, YELLOW, PALE = (255, 255, 255, 255), (255, 214, 64, 255), (255, 240, 160, 255)
OVERLAYS = []  # (png, start, end)


def title():
    def d(dr):
        dr.text((64, 40), "an unedited", font=font("DancingScript-Bold.ttf", 92), fill=WHITE)
        dr.text((150, 132), "day in my life", font=font("DancingScript-Bold.ttf", 92), fill=WHITE)
        dr.text((W // 2, H - 58), "2022", font=font("segoeui.ttf", 30), fill=WHITE, anchor="mm")
    return png("title", d)


def loc(key, name, sub):
    def d(dr):
        dr.text((52, 34), "@ " + name, font=font("DancingScript-Bold.ttf", 54), fill=YELLOW)
        dr.text((58, 102), sub, font=font("PlayfairDisplay-Italic.ttf", 26), fill=WHITE)
    return png("loc_" + key, d)


def cap(key, text, color=PALE, size=30):
    def d(dr):
        dr.text((W // 2, H - 62), text, font=font("segoeuib.ttf", size), fill=color, anchor="mm",
                stroke_width=3, stroke_fill=(20, 20, 20, 200))  # dark edge: readable on bright hoodies/skies
    return png("cap_" + key, d)


def credit():
    def d(dr):
        f = font("segoeui.ttf", 26)
        lines = ["edit test · apinvy style", "", "footage: Laurin Hwang, \"an UNEDITED day in my life\" (CC BY)",
                 "music: Kevin MacLeod (incompetech.com), CC BY 4.0", "sfx: synthesized"]
        for k, line in enumerate(lines):
            dr.text((W // 2, H // 2 - 70 + k * 38), line, font=f, fill=WHITE, anchor="mm")
    return png("credit", d)


OVERLAYS += [
    (title(), 0.3, at("intro") - 0.15),
    (loc("gym", "Orangetheory", "8:33 am · morning workout"), at("gym", 0.2), at("gym", 3.6)),
    (loc("derm", "the dermatologist", "Fullerton, CA"), at("laser", 1.8), at("laser", 5.4)),
    (loc("crumbl", "Crumbl Cookies", "post-laser cookie run"), at("crumbl", 0.1), at("crumbl", 3.6)),
    (loc("library", "the library", "picking up my holds"), at("library", 0.1), at("library", 3.6)),
    (loc("home", "home", "packages + reading time"), at("home", 0.1), at("home", 3.4)),
    (cap("irony", "...no cool transitions (sorry Laurin :)))"), at("irony", 3.2), seg_end("irony") + 0.3),
    (cap("red", "red. like, really red"), at("red", 2.6), at("red", 5.0)),
    (cap("egg", "an actual egg :)))"), at("egg", 0.6), seg_end("egg")),
    (cap("murder", "she did not murder anyone. it's the laser."), at("murder", 0.8), seg_end("murder")),
    (cap("stomach", "worth it"), at("stomach", 0.3), seg_end("stomach")),
    (cap("goal", "2022 goal: 45 books"), at("goal", 0.6), seg_end("goal")),
    (cap("ending", "[ no one's life is perfect ]", PALE, 26), at("ending", 4.5), TOTAL - 0.6),
]
CREDIT = credit()

# ---------------------------------------------------------------- audio
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def fade(x, ms=12):
    n = min(len(x) // 2, int(SR * ms / 1000))
    if n:
        r = np.linspace(0, 1, n)[:, None]
        x[:n] *= r
        x[-n:] *= r[::-1]
    return x


def place(buf, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += x * gain


N = int((TOTAL + 4.0) * SR)  # + credit card
src = SRC_AUDIO
speech = np.zeros((N, 2), np.float32)
for s in EDL:
    if s["audio"] == "mute":
        continue
    a, b = int((s["v"][0] - 0.04) * SR), int((s["v"][1] + 0.04) * SR)
    x = src[a:b].copy()
    fr = np.abs(x).max(axis=1)
    voiced = fr[fr > 0.03]
    rms = float(np.sqrt((voiced ** 2).mean())) if len(voiced) > SR // 10 else 0.0
    norm = float(np.clip(0.16 / rms, 0.5, 2.0)) if rms else 1.0
    place(speech, fade(x, 80) * s["gain"] * norm, s["t"] - 0.04)
for name, off, a_in, a_out, g in VO:
    place(speech, fade(src[int(a_in * SR):int(a_out * SR)].copy(), 40), at(name, off), g)

# music beds: (start, track, track offset, level)
# (start, track, offset into the track past its quiet intro, target RMS dBFS before ducking). The tracks differ
# by up to 12 dB, so each is normalised to its target (v2 review: music jumped loud at montage starts).
CUES = [(0.0, "Backbay_Lounge", 0.5, -20), (at("intro") - 1.0, "Wallpaper", 0.0, -27),
        (at("derm") - 0.3, "Lobby_Time", 1.5, -27), (at("crumbl_talk") - 0.2, "Carefree", 0.0, -27),
        (at("library_talk") - 0.3, "Bossa_Antigua", 0.5, -27), (at("ending") - 0.5, "Sincerely", 4.0, -24)]
music = np.zeros((N, 2), np.float32)
XF = 1.5
for k, (st, track, off, lvl) in enumerate(CUES):
    en = CUES[k + 1][0] + XF if k + 1 < len(CUES) else TOTAL
    full = load(os.path.join(MUSIC, track + ".mp3"))
    x = full[int(off * SR):int((off + en - st) * SR)].copy()
    fr = np.sqrt((full[: len(full) // SR * SR, 0].reshape(-1, SR) ** 2).mean(axis=1)) + 1e-6
    lvl = 10 ** ((lvl - 20 * np.log10(np.median(fr))) / 20)  # per-track gain to the target level
    n = int(XF * SR)
    x[:n] *= np.linspace(0, 1, n)[:, None]
    x[-n:] *= np.linspace(1, 0, n)[:, None]
    place(music, x, st, lvl)

# ducking: music drops ~14 dB while speech is present (smoothed envelope, fast attack, slow release)
env = np.abs(speech).max(axis=1)
hop = SR // 100
frames = env[: len(env) // hop * hop].reshape(-1, hop).max(axis=1)
active = (frames > 0.02).astype(float)
g = np.ones_like(active)
duck = 10 ** (-9 / 20)
level = 1.0
hold = 0
for i, a in enumerate(active):
    hold = 45 if a else max(0, hold - 1)  # stay ducked 450 ms after speech so short pauses don't pump the music
    target = duck if hold else 1.0
    level += (target - level) * (0.06 if target < level else 0.01)  # ~0.4 s down, ~1 s back up: no pumping, no jumps
    g[i] = level
gain = np.repeat(g, hop)
gain = np.pad(gain, (0, N - len(gain)), constant_values=1.0)[:N]
music *= gain[:, None]


# SFX, synthesized (no licensing question)
def shutter():
    t = np.arange(int(0.16 * SR)) / SR
    noise = np.random.default_rng(1).standard_normal(len(t))
    click = np.diff(noise, prepend=0) * (np.exp(-t * 90) + 0.8 * np.exp(-np.clip(t - 0.065, 0, None) * 110) * (t > 0.065))
    return np.stack([click, click], 1).astype(np.float32) * 0.14


def whoosh():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(2).standard_normal(n)
    out, y = np.zeros(n), 0.0
    for i in range(n):
        a = 0.02 + 0.25 * np.sin(np.pi * t[i] / 0.5) ** 2  # cutoff sweeps up then down
        y += a * (noise[i] - y)
        out[i] = y
    out *= np.sin(np.pi * t / 0.5) ** 1.5
    return np.stack([out, out * 0.9], 1).astype(np.float32) * 0.9


def chime():
    t = np.arange(int(1.2 * SR)) / SR
    x = (np.sin(2 * np.pi * 1568 * t) + 0.6 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t * 4)
    return np.stack([x, x], 1).astype(np.float32) * 0.06


SFX = {"shutter": shutter(), "whoosh": whoosh(), "chime": chime()}
FLASH = [end_of("murder") - 0.1, end_of("stomach") - 0.1]
EVENTS = [("shutter", FLASH[0] - 0.05), ("shutter", FLASH[1] - 0.05), ("chime", at("library") - 0.05)]
fx = np.zeros((N, 2), np.float32)
for name, t0 in EVENTS:
    place(fx, SFX[name], t0)

mix = speech + music + fx
fade_n = int(1.2 * SR)
end_i = int(TOTAL * SR)
mix[end_i - fade_n:end_i] *= np.linspace(1, 0, fade_n)[:, None]
mix[end_i:] = 0
mix /= max(1.0, np.abs(mix).max() / 0.97)
wav_path = os.path.join(TMP, "mix.wav")
with wave.open(wav_path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- video segments
# Cuts already in the source (Laurin trimmed her own ums). A segment edge landing a few frames from one of them
# shows a flash of the neighbouring shot (v1 review, 2:22). Fix: start/end the picture exactly on the source cut
# and hold the first/last clean frame for the gap; the audio is untouched, so lip-sync stays exact.
cuts_path = os.path.join(TMP, "src_cuts.json")
if not os.path.exists(cuts_path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", SRC, "-an", "-vf", r"scale=320:-2,select=gt(scene\,0.25),showinfo",
                          "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
    json.dump([float(m) for m in re.findall(r"pts_time:([\d.]+)", err)], open(cuts_path, "w"))
SRC_CUTS = json.load(open(cuts_path))
MIN_SHOT = 0.7   # no visible shot (between any two picture changes) may be shorter than this
MAX_SHIFT = 0.8  # how far a picture boundary may move off its audio boundary (J/L cut)

# Picture boundaries are moved off the audio boundaries (J/L cuts) so that no shot shorter than MIN_SHOT is
# ever shown: v1 flashed slivers of neighbouring source shots, v2 froze frames to hide them (both rejected
# in review). Moving boundary k by s_k keeps every segment in sync: segment i shows source
# [v0_i + s_{i-1}, v1_i + s_i] over timeline [t_i + s_{i-1}, t_i + dur_i + s_i].
N_SEG = len(EDL)


def shots_in(a, b):
    """Lengths of the visible shots inside source window [a, b] (edges count as picture changes)."""
    marks = [a] + [c for c in SRC_CUTS if a + 0.017 < c < b - 0.017] + [b]  # 1 source frame of slack
    return [y - x for x, y in zip(marks, marks[1:])]


def window_cost(i, s_in, s_out):
    """Badness of segment i shown over source [v0+s_in, v1+s_out]: short shots at either edge, and the shift."""
    a, b = EDL[i]["v"][0] + s_in, EDL[i]["v"][1] + s_out
    if b - a < MIN_SHOT:
        return 1e6
    # an edge that continues the same source as its neighbour is not a picture change
    cont_in = i > 0 and abs(EDL[i - 1]["v"][1] - EDL[i]["v"][0]) < 0.01
    cont_out = i + 1 < N_SEG and abs(EDL[i]["v"][1] - EDL[i + 1]["v"][0]) < 0.01
    lens = shots_in(a, b)
    first_bad = lens[0] < MIN_SHOT and not cont_in and (len(lens) > 1 or not cont_out)
    last_bad = len(lens) > 1 and lens[-1] < MIN_SHOT and not cont_out
    return 100 * first_bad + 100 * last_bad + 0.5 * abs(s_out)


def candidates(k):
    """Shifts for boundary k: none, or put it just before a source cut near the end of EDL[k] /
    just after a source cut near the start of EDL[k+1]."""
    A, B = EDL[k], EDL[k + 1]
    c = {0.0}
    for cut in SRC_CUTS:
        contiguous = abs(A["v"][1] - B["v"][0]) < 0.01
        ds = (cut - 0.04 - A["v"][1], cut + 0.04 - B["v"][0]) + ((cut - A["v"][1],) if contiguous else ())
        for d in ds:  # exactly on a cut only where both sides are the same continuous source
            if abs(d) <= MAX_SHIFT:
                c.add(round(d, 3))
    return sorted(c)


# Dynamic programming over the boundary shifts: state = shift of the boundary before segment i.
best = {0.0: (0.0, [0.0])}
for i in range(N_SEG):
    outs = candidates(i) if i < N_SEG - 1 else [0.0]
    nxt = {}
    for s_out in outs:
        for s_in, (c, path) in best.items():
            cc = c + window_cost(i, s_in, s_out)
            if s_out not in nxt or cc < nxt[s_out][0]:
                nxt[s_out] = (cc, path + [s_out])
    best = nxt
SHIFTS = best[0.0][1]  # SHIFTS[i] = shift of the boundary before segment i, SHIFTS[i+1] = after it

# Picture boundaries on the 30 fps grid, so per-segment frame rounding cannot drift the picture off the audio.
PB = [round((EDL[i]["t"] + SHIFTS[i]) * FPS) for i in range(N_SEG)] + [round(TOTAL * FPS)]

# Text that starts at a segment must wait for that segment's picture (J/L shifts move it by up to 0.8 s).
for j, (pth, o_a, o_b) in enumerate(OVERLAYS):
    for i, sg in enumerate(EDL):
        if sg["t"] <= o_a < sg["t"] + sg["dur"]:
            pic = PB[i] / FPS
            if o_a < pic + 0.1:
                OVERLAYS[j] = (pth, pic + 0.1, max(o_b, pic + 1.0))
            break

seg_list = os.path.join(TMP, "segs.txt")
short_left = []
with open(seg_list, "w") as f:
    for k, s in enumerate(EDL):
        path = os.path.join(TMP, "seg", f"{k:03}.mp4")
        frames = PB[k + 1] - PB[k]
        a = s["v"][0] + (PB[k] / FPS - s["t"])   # same source<->timeline mapping as the audio: stays in sync
        b = a + frames / FPS
        lens = shots_in(a, b)
        hold_in = hold_out = 0.0
        parts = None
        if s.get("vo") and (s.get("vsrc") or any(x < MIN_SHOT for x in lens)):
            # voice-over: walk the source from `a` (or the chosen picture start), keeping only shots >= MIN_SHOT
            v_from = s.get("vsrc") or a
            marks = [v_from] + [c for c in SRC_CUTS if v_from + 0.035 < c < v_from + 30] + [v_from + 30]
            parts, need = [], frames
            for x, y in zip(marks, marks[1:]):
                if y - x >= MIN_SHOT and need > 0:
                    n = min(need, int((y - x - 0.02) * FPS))
                    parts.append((x + 0.01, n))
                    need -= n
            lens = [n / FPS for _, n in parts]
        else:
            # an edge sliver too small to see as a freeze (<= 0.15 s, ~4 frames) is covered by the clean frame
            if len(lens) > 1 and lens[0] < MIN_SHOT and lens[0] <= 0.15:
                hold_in, a = round(lens[0], 3), a + lens[0]
                lens = lens[1:]
            if len(lens) > 1 and lens[-1] < MIN_SHOT and lens[-1] <= 0.15:
                hold_out = round(lens[-1], 3)
                lens = lens[:-1]
        short_left += [(round(s["t"] + SHIFTS[k], 2), round(x, 2)) for x in lens if x < MIN_SHOT]
        push = s["zoom"] - 1.0
        if push > 0:  # slow push-in instead of a jump punch-in (v2 review: short punch-ins read as foreign frames)
            push = min(push, 0.03 * (b - a), 0.10)
            n = max(1, int((b - a) * FPS))
            zp = (f",zoompan=z='1+{push:.4f}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":d=1:s={W}x{H}:fps={FPS}")
        else:
            zp = ""
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1," \
             f"fps={FPS}{zp},format=yuv420p"
        if hold_in or hold_out:
            vf += f",tpad=start_mode=clone:start_duration={hold_in}:stop_mode=clone:stop_duration={hold_out}"
        key = f"{a:.3f}-{frames}-{push:.4f}-{hold_in}-{hold_out}-{parts}"
        stamp = path + ".key"
        if not (os.path.exists(path) and os.path.exists(stamp) and open(stamp).read() == key):
            if parts:
                sub = []
                done_frames = 0
                for j, (pa, n) in enumerate(parts):
                    pp = path.replace(".mp4", f"_p{j}.mp4")
                    pvf = vf.replace("*on/", f"*(on+{done_frames})/") if zp else vf
                    done_frames += n
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{pa:.3f}", "-t", f"{n / FPS + 0.2:.3f}",
                                    "-i", SRC, "-vf", pvf, "-frames:v", str(n), "-an", "-c:v", "libx264",
                                    "-preset", "veryfast", "-crf", "18", pp], check=True)
                    sub.append(pp)
                lst = path.replace(".mp4", "_parts.txt")
                open(lst, "w").write("".join(f"file '{q.replace(os.sep, '/')}'\n" for q in sub))
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                                path], check=True)
            else:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a + 0.2:.3f}", "-i", SRC,
                                "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "veryfast",
                                "-crf", "18", path], check=True)
            open(stamp, "w").write(key)
        f.write(f"file '{path.replace(os.sep, '/')}'\n")
print(f"J/L shifts on {sum(1 for x in SHIFTS if x)} boundaries; shots < {MIN_SHOT}s left: {short_left}")
base = os.path.join(TMP, "base.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", seg_list, "-c", "copy", base], check=True)

# ---------------------------------------------------------------- final composite
white = os.path.join(TMP, "png", "white.png")
Image.new("RGBA", (W, H), (255, 255, 255, 165)).save(white)  # softer flash
inputs, chain, last = ["-i", base, "-i", wav_path], [], "[0:v]"
chain.append(f"[0:v]tpad=stop_mode=add:stop_duration=4:color=black,fade=t=out:st={TOTAL - 1.2}:d=1.2[v0]")
last, idx = "[v0]", 2
layers = [(p, a, b, 0.25) for p, a, b in OVERLAYS] + [(white, t0, t0 + 0.35, 0.0) for t0 in FLASH] + \
         [(CREDIT, TOTAL + 0.3, TOTAL + 3.8, 0.4)]
for k, (p, a, b, fd) in enumerate(layers):
    d = round(b - a, 3)
    inputs += ["-loop", "1", "-t", str(d), "-i", p]
    if fd:
        f = f"fade=t=in:st=0:d={fd}:alpha=1,fade=t=out:st={max(0, d - fd)}:d={fd}:alpha=1"
    else:
        f = f"fade=t=out:st=0:d={d}:alpha=1"
    chain.append(f"[{idx}:v]format=rgba,{f},setpts=PTS-STARTPTS+{a}/TB[o{k}]")
    chain.append(f"{last}[o{k}]overlay=0:0:eof_action=pass:format=auto[v{k + 1}]")
    last, idx = f"[v{k + 1}]", idx + 1
out = os.path.join(OUT, f"{VERSION}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", last, "-map", "1:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-t", str(TOTAL + 4.0), "-movflags", "+faststart", out], check=True)

# ---------------------------------------------------------------- transcript (.srt) of the cut, for FrameJam
def ts(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")


cues = []
spans = [(s["v"][0], s["v"][1], s["t"]) for s in EDL if s["audio"] == "src" and s["gain"] >= 0.9]
spans += [(a_in, a_out, at(n, off)) for n, off, a_in, a_out, _ in VO]
for a, b, t0 in spans:
    ws = [(wt - a + t0, w) for wt, w, _ in WORDS if a <= wt < b]
    for i in range(0, len(ws), 7):
        chunk = ws[i:i + 7]
        end = ws[i + 7][0] if i + 7 < len(ws) else t0 + (b - a)
        cues.append((chunk[0][0], end, " ".join(w for _, w in chunk)))
cues.sort()
with open(os.path.join(OUT, f"{VERSION}.srt"), "w", encoding="utf-8") as f:
    for k, (a, b, text) in enumerate(cues, 1):
        f.write(f"{k}\n{ts(a)} --> {ts(b)}\n{text}\n\n")
json.dump({"total": TOTAL, "segments": [{k: s[k] for k in ("name", "t", "dur", "v", "zoom", "audio")} for s in EDL]},
          open(os.path.join(OUT, f"{VERSION}_edl.json"), "w"), indent=1)
print(f"{out}  {TOTAL:.1f}s + 4s credit, {len(EDL)} segments")
