"""Turn a YouTube video (or a local mp4) into something an agent can read: shot list,
contact sheets with timestamps, transcript, and optionally Gemini's edit log (it hears SFX/music).

usage: py tools/watch_video.py <youtube url | file.mp4> [name] [--gemini] [--gemini-only] [--scene=0.25]
  --gemini       also send the video to Gemini (in CHUNK-second pieces) for an edit log
  --gemini-only  reuse an earlier run's video/report and only (re)do the Gemini part
writes reference/youtube/<name>/: video.mp4, report.md, sheets/sheet_NN.jpg, [gemini.json]"""
import json, os, re, statistics as st, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

from paths import REFERENCE

sys.stdout.reconfigure(encoding="utf-8")
opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
SCENE = float(opts.get("scene", 0.25))  # ffmpeg scene-change threshold; 0.25 ignores handheld camera shake
MIN_SHOT = 0.25    # cuts closer than this are merged (flashes would otherwise split into dozens of shots)
LONG_SHOT = 4.0    # long shots get one extra frame every LONG_SHOT seconds (catches overlays without a cut)
THUMB = 320        # longest side of a thumbnail
COLS, ROWS = 4, 4  # thumbnails per contact sheet
CHUNK = int(opts.get("chunk", 480))  # Gemini gets the video in pieces: one 45-min upload loses detail late on

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    raise SystemExit(__doc__)
src, gemini_only = args[0], "--gemini-only" in sys.argv
use_gemini = gemini_only or "--gemini" in sys.argv


def fmt(t):
    return f"{int(t // 60):02}:{t % 60:04.1f}"


def download(url, out):
    import yt_dlp
    opts = {"outtmpl": os.path.join(out, "video.%(ext)s"), "merge_output_format": "mp4",
            "format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/b", "subtitlesformat": "json3",
            "js_runtimes": {"node": {}, "deno": {}}, "quiet": True, "noprogress": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=False)
    # Only captions in the video's own language: auto-translated ones (e.g. 'vi' of an English video) hit 429s
    manual = [k for k in info.get("subtitles") or {} if k != "live_chat"]  # premieres list their chat as a "sub"
    auto = [k for k in info.get("automatic_captions") or {} if k.endswith("-orig")]
    lang = (manual or auto or [None])[0]
    if lang:
        try:
            with yt_dlp.YoutubeDL({**opts, "writesubtitles": bool(manual), "writeautomaticsub": not manual,
                                   "subtitleslangs": [lang]}) as y:
                y.process_ie_result(info, download=True)
        except yt_dlp.utils.DownloadError as e:
            print(f"  captions failed ({e}), falling back to whisper", flush=True)
            lang = None
    if not lang:
        with yt_dlp.YoutubeDL(opts) as y:
            y.process_ie_result(info, download=True)
    return {k: info.get(k) for k in ("title", "channel", "upload_date", "duration", "view_count", "webpage_url")}


def subtitle_lines(out):
    """YouTube json3 captions -> [(start, end, text)]; manual subs win over auto ones (named *.en-orig etc.)."""
    files = sorted((f for f in os.listdir(out) if f.endswith(".json3")), key=lambda f: ("orig" in f, f))
    if not files:
        return None, None
    lines = []
    for e in json.load(open(os.path.join(out, files[0]), encoding="utf-8")).get("events", []):
        text = "".join(s.get("utf8", "") for s in e.get("segs", [])).strip()
        if text:
            t0 = e["tStartMs"] / 1000
            lines.append((t0, t0 + e.get("dDurationMs", 0) / 1000, text.replace("\n", " ")))
    return lines, files[0]


def whisper_lines(video):
    from faster_whisper import WhisperModel
    print("no captions, transcribing with faster-whisper...", flush=True)
    model = WhisperModel("small", device="cpu", compute_type="int8")
    parts, _ = model.transcribe(video, beam_size=5, vad_filter=True)
    return [(p.start, p.end, p.text.strip()) for p in parts]


def probe(video):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:format=duration", "-of", "json", video],
                                  capture_output=True, check=True).stdout)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def cuts(video):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-an", "-vf",
                          f"scale=320:-2,select='gt(scene,{SCENE})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", err)]


def grab(video, t, path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                    f"scale='if(gt(iw,ih),{THUMB},-2)':'if(gt(iw,ih),-2,{THUMB})'", path], check=True)


def contact_sheets(video, shots, out):
    """One frame per shot (more for long shots), tiled with '#shot mm:ss.s' labels."""
    frames_dir = os.path.join(out, "frames")
    sheets_dir = os.path.join(out, "sheets")
    for d in (frames_dir, sheets_dir):
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    picks = []
    for i, (a, b) in enumerate(shots, 1):
        n = max(1, int((b - a) // LONG_SHOT))
        picks += [(i, a + (b - a) * (k + 0.5) / n) for k in range(n)]
    paths = [os.path.join(frames_dir, f"{k:04}.jpg") for k in range(len(picks))]
    with ThreadPoolExecutor(6) as pool:
        list(pool.map(lambda p: grab(video, p[0][1], p[1]), zip(picks, paths)))
    try:
        font = ImageFont.truetype("arialbd.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    w, h = Image.open(paths[0]).size
    per = COLS * ROWS
    sheets = []
    for s in range(0, len(picks), per):
        chunk = list(zip(picks[s:s + per], paths[s:s + per]))
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * w, rows * h), "black")
        draw = ImageDraw.Draw(sheet)
        for k, ((shot, t), p) in enumerate(chunk):
            x, y = k % COLS * w, k // COLS * h
            sheet.paste(Image.open(p).resize((w, h)), (x, y))
            label = f"#{shot} {fmt(t)}"
            draw.rectangle(draw.textbbox((x + 4, y + 4), label, font=font), fill="black")
            draw.text((x + 4, y + 4), label, fill="yellow", font=font)
        name = f"sheet_{len(sheets) + 1:02}.jpg"
        sheet.save(os.path.join(sheets_dir, name), quality=80)
        sheets.append((name, chunk[0][0][0], chunk[-1][0][0]))
    return sheets


PROMPT = """You are a professional video editor studying how this travel/lifestyle vlog is edited so you can
replicate the style. This clip is one piece of a longer video; it starts at {start} of the full video.
Use timestamps relative to THIS clip (m:ss.s, as a string). Keep spoken quotes in their original language.

Return JSON: {{"events": [{{"t": "m:ss.s", "type": "...", "what": "..."}}], "summary": {{...}}}}
event types: cut | jcut | lcut | broll | talk_to_camera | voiceover | music | sfx | ambient | text | title |
transition | speed | zoom | map | photo | other.
Log every notable edit event in order: music starting/stopping/changing (genre, mood, with/without vocals,
ducked under speech or not), whether speech is to-camera, voiceover over b-roll, or captured live; sound
design (whooshes, pops, natural sound bursts, silence beats); J/L-cuts where audio leads or trails a cut;
on-screen text (exact words, font style, position, purpose); transitions other than hard cuts; speed ramps,
timelapses, slow motion; zooms/punch-ins; maps, photos, screenshots, freeze frames.

summary keys: "structure" (what happens in this clip, in segments with times), "pacing" (how fast cuts are and
how that changes), "music" (style and how it is used), "voice" (how the creator talks: tone, to-camera vs
voiceover, humour), "sound_design", "text_style", "visual_style" (shots, framing, colour grade, camera moves),
"signature_moves" (anything distinctive a copycat editor must do)."""


def to_seconds(t):
    m, _, s = str(t or 0).rpartition(":")  # asked as a string: bare numbers came back as mmss (104 for 1:04)
    try:
        return float(m or 0) * 60 + float(s)
    except ValueError:
        return 0.0


def gemini_log(video, out, duration):
    from gemini import generate_json, video_part
    chunks_dir = os.path.join(out, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    def one(start):
        path = os.path.join(chunks_dir, f"{int(start):05}.mp4")
        done = path[:-4] + ".json"  # finished chunks are kept so a rerun after a quota error skips them
        if os.path.exists(done):
            return json.load(open(done, encoding="utf-8"))
        if not os.path.exists(path):  # 360p is plenty for editing analysis and uploads fast
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(CHUNK), "-i", video,
                            "-vf", "scale=-2:360", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                            "-c:a", "aac", "-b:a", "96k", path], check=True)
        print(f"  gemini chunk {fmt(start)} ...", flush=True)
        res = generate_json([video_part(path), {"text": PROMPT.format(start=fmt(start))}], timeout=900)
        if isinstance(res, list):  # sometimes the whole answer comes wrapped in a list: [{"events":..., "summary":...}]
            res = res[0] if len(res) == 1 and isinstance(res[0], dict) and "events" in res[0] else {"events": res}
        events = [e for e in res.get("events", []) if isinstance(e, dict)]
        for e in events:
            e["t"] = round(start + to_seconds(e.get("t")), 1)
        part = {"start": start, "events": events, "summary": res.get("summary", {})}
        json.dump(part, open(done, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return part

    with ThreadPoolExecutor(int(opts.get("workers", 2))) as pool:
        parts = list(pool.map(one, range(0, int(duration), CHUNK)))
    json.dump(parts, open(os.path.join(out, "gemini.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return parts


def gemini_section(parts):
    r = ["", "## Gemini (`gemini.json`, timestamps approximate ±1-2s)", ""]
    for p in parts:
        r += [f"### Chunk from {fmt(p['start'])}", ""]
        for k, v in (p.get("summary") or {}).items():
            r.append(f"- **{k}**: {json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}")
        r.append("")
        r += [f"- {fmt(e['t'])} {e.get('type')}: {e.get('what')}" for e in p["events"]]
        r.append("")
    return r


is_url = re.match(r"https?://", src)
name = args[1] if len(args) > 1 else (re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", src) or
                                      re.search(r"([^/\\]+?)(\.\w+)?$", src)).group(1)
out = os.path.join(REFERENCE, "youtube", name)
os.makedirs(out, exist_ok=True)
video = os.path.join(out, "video.mp4")
meta_path = os.path.join(out, "meta.json")
if is_url and not os.path.exists(video):
    print(f"downloading {src} ...", flush=True)
    json.dump(download(src, out), open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
elif not is_url:
    video = os.path.abspath(src)
meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {"title": os.path.basename(src)}

width, height, duration = probe(video)
report_path = os.path.join(out, "report.md")
if gemini_only:
    if not os.path.exists(report_path):
        raise SystemExit("no report.md yet: run without --gemini-only first")
    body = open(report_path, encoding="utf-8").read().split("\n## Gemini")[0].rstrip("\n").split("\n")
    print("uploading to Gemini for an edit log...", flush=True)
    body += gemini_section(gemini_log(video, out, duration))
    open(report_path, "w", encoding="utf-8").write("\n".join(body) + "\n")
    print(f"updated {report_path}")
    sys.exit(0)

print("detecting cuts...", flush=True)
bounds = [0.0]
for t in cuts(video) + [duration]:
    if t - bounds[-1] >= MIN_SHOT:
        bounds.append(t)
bounds[-1] = duration
shots = list(zip(bounds, bounds[1:]))
print(f"{len(shots)} shots, extracting frames...", flush=True)
sheets = contact_sheets(video, shots, out)

lines, sub_file = subtitle_lines(out)
source = f"YouTube captions ({sub_file})" if lines else "faster-whisper"
if lines is None:
    lines = whisper_lines(video)

events = None
if use_gemini:
    print("uploading to Gemini for an edit log...", flush=True)
    try:
        events = gemini_log(video, out, duration)
    except Exception as e:  # optional extra: the report is still useful without it
        print(f"  gemini failed: {e}")

durs = sorted(b - a for a, b in shots)
q = lambda p: durs[min(len(durs) - 1, int(p * len(durs)))]
r = [f"# {meta.get('title')}", "",
     f"- source: {meta.get('webpage_url') or video}",
     f"- channel: {meta.get('channel')}, uploaded {meta.get('upload_date')}, {meta.get('view_count')} views",
     f"- {width}x{height}, {duration:.1f}s, video: `{video}`",
     f"- {len(shots)} shots ({len(shots) / duration * 60:.0f}/min), shot length p25/median/p75 "
     f"{q(.25):.2f}/{st.median(durs):.2f}/{q(.75):.2f}s, longest {durs[-1]:.1f}s",
     f"- transcript: {source}", "",
     "## Contact sheets (`sheets/`, each label is `#shot mm:ss.s`)", ""]
r += [f"- `{n}`: shots {a}–{b}" for n, a, b in sheets]
r += ["", "## Timeline (shot, start, length, speech during the shot)", ""]
for i, (a, b) in enumerate(shots, 1):
    said = " / ".join(t for s, e, t in lines if s < b and e > a and s >= a - 0.5)
    r.append(f"- #{i} {fmt(a)} {b - a:.1f}s" + (f" — {said}" if said else ""))
if events:
    r += gemini_section(events)
open(report_path, "w", encoding="utf-8").write("\n".join(r) + "\n")
print(f"wrote {os.path.join(out, 'report.md')} ({len(sheets)} sheets, {len(lines)} transcript lines)")
