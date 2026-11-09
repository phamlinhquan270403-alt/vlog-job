"""Minimal Gemini REST client shared by the pipeline steps.

Several keys can be listed in .env (GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, ...): when one hits
its daily free-tier quota the next one takes over, and a key that only hit the per-minute limit rests while
the others work. Uploaded videos belong to the key that uploaded them, so they are re-uploaded on a switch."""
import base64, json, os, re, subprocess, threading, time, urllib.error, urllib.request, winreg

MODELS = ["gemini-3-flash-preview", "gemini-3.8-flash"]  # preferred first; every key is tried on a model first
ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
_lock = threading.Lock()
_spent = set()   # (key, model) pairs whose daily quota is used up
_resting = {}    # (key, model) -> time.time() when the per-minute limit lifts


def api_keys():
    """.env first (re-read on every call, so keys added mid-run are picked up), then the env var, then the registry."""
    keys = []
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8-sig"):
            name, _, value = line.strip().partition("=")
            value = value.strip().strip('"\'')
            if re.fullmatch(r"GEMINI_API_KEY(_\d+)?", name.strip()) and value and value not in keys:
                keys.append(value)
    if not keys:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                    key = winreg.QueryValueEx(k, "GEMINI_API_KEY")[0]
            except OSError:
                pass
        keys = [key] if key else []
    if not keys:
        raise RuntimeError(f"GEMINI_API_KEY is empty: paste your key into {ENV}")
    return keys


def api_key():
    return api_keys()[0]


def _pick():
    """Best (key, model) right now: preferred model on any key before a fallback model. Returns (key, model, wait)."""
    keys, now = api_keys(), time.time()
    with _lock:
        live = [(k, m) for m in MODELS for k in keys if (k, m) not in _spent]
        if not live:
            raise RuntimeError(f"all {len(keys)} key(s) used up their daily quota: add GEMINI_API_KEY_{len(keys) + 1} "
                               f"to {ENV} or wait for the reset (midnight Pacific time)")
        ready = [p for p in live if _resting.get(p, 0) <= now]
        if ready:
            return (*ready[0], 0)
        k, m = min(live, key=lambda p: _resting[p])
        return k, m, _resting[(k, m)] - now


def _label(key):
    return f"key#{api_keys().index(key) + 1}" if key in api_keys() else "key"


def image_part(path, max_side=640):
    """Downscale with ffmpeg so huge meme templates don't blow up the request."""
    data = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf",
         f"scale='min({max_side},iw)':'min({max_side},ih)':force_original_aspect_ratio=decrease",
         "-frames:v", "1", "-f", "image2pipe", "-c:v", "mjpeg", "-"],
        capture_output=True, check=True).stdout
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(data).decode()}}


def audio_part(path):
    return {"inline_data": {"mime_type": "audio/mpeg", "data": base64.b64encode(open(path, "rb").read()).decode()}}


def video_part(path):
    """A video for generate_json: uploaded lazily, once per key, when a request actually goes out."""
    return {"_video": path}


def _upload(path, key):
    """Upload through the Files API (too big for inline_data) and wait until Gemini has processed it."""
    size = os.path.getsize(path)
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/upload/v1beta/files", method="POST",
        data=json.dumps({"file": {"display_name": os.path.basename(path)}}).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json",
                 "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(size), "X-Goog-Upload-Header-Content-Type": "video/mp4"})
    with urllib.request.urlopen(req, timeout=60) as r:
        upload_url = r.headers["X-Goog-Upload-URL"]
    req = urllib.request.Request(upload_url, data=open(path, "rb").read(), method="POST", headers={
        "X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize"})
    with urllib.request.urlopen(req, timeout=600) as r:
        f = json.load(r)["file"]
    while f["state"] == "PROCESSING":
        time.sleep(5)
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{f['name']}",
                                     headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=60) as r:
            f = json.load(r)
    if f["state"] != "ACTIVE":
        raise RuntimeError(f"Gemini could not process {path}: {f['state']}")
    return {"file_data": {"mime_type": "video/mp4", "file_uri": f["uri"]}}


def generate_json(parts, temperature=0.2, timeout=150, **config):
    """config goes into generationConfig, e.g. mediaResolution="MEDIA_RESOLUTION_LOW" for long videos.
    Quota errors (429) switch keys/models without counting as a failed attempt; other errors get 6 tries."""
    gen = {"response_mime_type": "application/json", "temperature": temperature, **config}
    uploads = {}  # (key, path) -> file_data part
    failures = 0
    while True:
        key, model, wait = _pick()
        if wait > 0:
            print(f"  every key is rate-limited, waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
            continue
        who = f"{_label(key)} {model}"
        try:
            sent = []
            for p in parts:
                if "_video" in p:
                    if (key, p["_video"]) not in uploads:
                        uploads[(key, p["_video"])] = _upload(p["_video"], key)
                    p = uploads[(key, p["_video"])]
                sent.append(p)
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=json.dumps({"contents": [{"parts": sent}], "generationConfig": gen}).encode(), method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": key})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.load(r)
            return json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            text = e.read().decode(errors="replace")
            if e.code == 429:
                quota = (re.search(r'"quotaId":\s*"([^"]+)', text) or [None, ""])[1]
                delay = re.search(r'"retryDelay":\s*"(\d+)', text)
                with _lock:
                    if "PerDay" in quota:
                        _spent.add((key, model))
                    else:  # per-minute limit: rest this pair, others keep going
                        _resting[(key, model)] = time.time() + (int(delay.group(1)) + 3 if delay else 30)
                print(f"  {who}: 429 {quota or 'quota'} -> {'switching' if 'PerDay' in quota else 'resting'}",
                      flush=True)
                continue
            print(f"  {who}: {e.code} {text[:300]}", flush=True)
            if e.code not in (500, 503, 504):
                raise
        except (TimeoutError, OSError) as e:
            print(f"  {who}: {e}", flush=True)
        failures += 1
        if failures == 6:
            raise RuntimeError("Gemini did not answer after 6 attempts")
        with _lock:  # overloaded/timeout: let this pair cool off so the next try may use another one
            _resting[(key, model)] = time.time() + 5 * failures
        time.sleep(5 * failures)
