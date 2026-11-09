"""Let the Claude API (Haiku 5.5 only) do the bulk *reading* of images and files, so contact sheets and
frames do not eat the Claude Code Pro plan's usage. The *analysis* (style guides, synthesis) is done by
Claude Code itself on the Pro plan, from the small text files this script writes.

usage:
  py tools/claude_read.py sheets [video_id...]   # every contact sheet -> claude_visual.json + claude_visual_log.md
                                                 # (compact text log for the Claude Code session to analyse)
  py tools/claude_read.py ask <file> [file...] -q "question" [--out=answer.md]   # Haiku reads, e.g. OCR / tagging
  py tools/claude_read.py cost                   # money spent so far vs CLAUDE_BUDGET_USD

ANTHROPIC_API_KEY and CLAUDE_BUDGET_USD are read from .env only (not exported: an exported ANTHROPIC_API_KEY
would make Claude Code bill the API instead of the Pro plan). Every call is logged to logs/claude_usage.jsonl
and the script stops before a call once the budget is spent."""
import base64, io, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor

import anthropic
from PIL import Image

from paths import REFERENCE, ROOT

sys.stdout.reconfigure(encoding="utf-8")
ENV = os.path.join(ROOT, ".env")
USAGE_LOG = os.path.join(ROOT, "logs", "claude_usage.jsonl")
MODELS = {"haiku": "claude-haiku-5-5"}  # Sonnet/Opus are off: analysis belongs to the Claude Code Pro session
# $ per 1M tokens (input, output). Haiku 5.5 costs more once a prompt passes 100K tokens.
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-haiku-5-5@long": (0.50, 2.50), "claude-sonnet-5-5": (2.00, 10.00)}
IMAGE_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
MAX_SIDE = 1568  # Claude downsizes anything bigger anyway; sending less keeps requests small


def env(name, default=None):
    if os.path.exists(ENV):
        for line in open(ENV, encoding="utf-8-sig"):
            k, _, v = line.strip().partition("=")
            if k.strip() == name and v.strip():
                return v.strip().strip('"\'')
    return default


def model_id(name):
    name = name.lower()
    if any(k in name for k in ("opus", "fable", "mythos", "sonnet")):
        raise SystemExit("only Haiku runs on the API key here; let Claude Code (Pro plan) do the analysis instead")
    if name in MODELS:
        return MODELS[name]
    if name in MODELS.values():
        return name
    raise SystemExit(f"unknown model {name}: only haiku is allowed")


def spent():
    if not os.path.exists(USAGE_LOG):
        return 0.0
    return sum(json.loads(l)["usd"] for l in open(USAGE_LOG, encoding="utf-8") if l.strip())


def cost(model, usage):
    prompt = usage.input_tokens + (usage.cache_creation_input_tokens or 0) + (usage.cache_read_input_tokens or 0)
    pin, pout = PRICE[f"{model}@long" if model.startswith("claude-haiku") and prompt > 100_000 else model]
    uncached = usage.input_tokens + 1.25 * (usage.cache_creation_input_tokens or 0) + 0.1 * (usage.cache_read_input_tokens or 0)
    return (uncached * pin + usage.output_tokens * pout) / 1e6


_client = None


def client():
    global _client
    if _client is None:
        key = env("ANTHROPIC_API_KEY")
        if not key:
            raise SystemExit(f"ANTHROPIC_API_KEY is empty: paste your key into {ENV}")
        _client = anthropic.Anthropic(api_key=key, max_retries=4)
    return _client


def call(model, content, task, max_tokens=8000, effort="low", schema=None, system=None):
    """One request with budget check + usage log. Returns parsed JSON when schema is given, else text."""
    budget = float(env("CLAUDE_BUDGET_USD", "100"))
    if spent() >= budget:
        raise SystemExit(f"budget used up: ${spent():.2f} of ${budget:.2f} (raise CLAUDE_BUDGET_USD in .env)")
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kwargs = {"system": system} if system else {}
    with client().messages.stream(model=model, max_tokens=max_tokens, output_config=output_config,
                                  messages=[{"role": "user", "content": content}], **kwargs) as stream:
        msg = stream.get_final_message()
    usd = cost(model, msg.usage)
    os.makedirs(os.path.dirname(USAGE_LOG), exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "task": task, "model": model,
                            "in": msg.usage.input_tokens, "out": msg.usage.output_tokens,
                            "usd": round(usd, 5)}) + "\n")
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"{task}: Claude declined ({getattr(msg.stop_details, 'category', None)})")
    text = "".join(b.text for b in msg.content if b.type == "text")
    if msg.stop_reason == "max_tokens":
        print(f"  warning: {task} hit max_tokens, answer may be cut", flush=True)
    return json.loads(text) if schema else text


def file_block(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        im = Image.open(path)
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=85)
        return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                            "data": base64.standard_b64encode(buf.getvalue()).decode()}}
    if ext == ".pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                               "data": base64.standard_b64encode(open(path, "rb").read()).decode()}}
    return {"type": "text", "text": f"<file name=\"{os.path.basename(path)}\">\n"
                                    f"{open(path, encoding='utf-8', errors='replace').read()}\n</file>"}


# ---------- sheets: per contact sheet visual log, then a style summary ----------

SHEET_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["frames"],
    "properties": {"frames": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["label", "shot", "camera", "subject", "text_on_screen", "text_style", "notes"],
        "properties": {
            "label": {"type": "string", "description": "the yellow '#shot mm:ss.s' label, copied exactly"},
            "shot": {"type": "string", "enum": ["selfie", "pov", "wide", "medium", "closeup", "aerial", "screen",
                                                "title_card", "black", "split_screen", "other"]},
            "camera": {"type": "string", "enum": ["handheld", "gimbal", "tripod", "drone", "phone_screen", "unknown"]},
            "subject": {"type": "string", "description": "what is shown, max 12 words"},
            "text_on_screen": {"type": "string", "description": "overlay text copied exactly ('' if none); ignore the yellow label"},
            "text_style": {"type": "string", "description": "font kind, colour, size, position ('' if no text)"},
            "notes": {"type": "string", "description": "transition hints, effects, framing, colour grade ('' if nothing)"}}}}}}

SHEET_PROMPT = """This image is a contact sheet from a travel vlog: a grid of thumbnails, one per shot, each with a
yellow label '#shot mm:ss.s' in its top-left corner (added by our tool, not part of the video).
For every thumbnail, left to right, top to bottom, describe it for an editor who wants to copy the channel's
editing style. Copy any on-screen text exactly, in its original language."""

SUMMARY_PROMPT = """You are a senior video editor. Below are (1) pacing stats and transcript excerpts from report.md,
(2) a per-shot visual log of a travel vlog made from contact sheets, and (3) if present, Gemini's audio/edit notes.
Write, in Vietnamese, a concise style guide another editor can follow to copy this channel:
## Cấu trúc (mở đầu, thân, kết; mốc thời gian)
## Hình ảnh (loại shot, máy quay, tỉ lệ selfie/drone/POV, màu)
## Chữ trên màn hình (từng loại: title, nhãn địa điểm, phụ đề, kiểu chữ, màu, vị trí, ví dụ thật)
## Chuyển cảnh và hiệu ứng
## Âm thanh (chỉ khi có ghi chú Gemini)
## Công thức làm lại (checklist 8-12 bước)
Cite timestamps as evidence. Only state what the data supports."""


def sheets(video_id, model):
    out = os.path.join(REFERENCE, "youtube", video_id)
    sheet_dir = os.path.join(out, "sheets")
    if not os.path.isdir(sheet_dir):
        raise SystemExit(f"no {sheet_dir}: run tools/watch_video.py first")
    cache_dir = os.path.join(out, "claude_sheets")
    os.makedirs(cache_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(sheet_dir) if f.endswith(".jpg"))

    def one(name):
        done = os.path.join(cache_dir, name.replace(".jpg", ".json"))
        if os.path.exists(done):  # reruns skip sheets already paid for
            return json.load(open(done, encoding="utf-8"))
        res = call(model, [file_block(os.path.join(sheet_dir, name)), {"type": "text", "text": SHEET_PROMPT}],
                   task=f"sheet {video_id}/{name}", schema=SHEET_SCHEMA, effort="low")
        json.dump(res, open(done, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {name}: {len(res['frames'])} frames", flush=True)
        return res

    print(f"{video_id}: {len(names)} sheets with {model} (spent so far ${spent():.3f})", flush=True)
    with ThreadPoolExecutor(4) as pool:
        frames = [f for r in pool.map(one, names) for f in r["frames"]]
    json.dump(frames, open(os.path.join(out, "claude_visual.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # Compact text log: one line per shot. The Claude Code session reads this (plus report.md) and writes the
    # style guide itself, following ANALYSIS_BRIEF below, instead of paying for Sonnet.
    log = [f"# Visual log {video_id} (Haiku from contact sheets; small text may be misread, check frames)", ""]
    log += [f"{f['label']} | {f['shot']} | {f['camera']} | {f['subject']}"
            + (f" | TEXT: {f['text_on_screen']} ({f['text_style']})" if f["text_on_screen"] else "")
            + (f" | {f['notes']}" if f["notes"] else "") for f in frames]
    path = os.path.join(out, "claude_visual_log.md")
    open(path, "w", encoding="utf-8").write("\n".join(log) + "\n")
    print(f"wrote {path} (total spent ${spent():.3f})")


# What the Claude Code session should write after `sheets` (kept here so every run uses the same brief).
ANALYSIS_BRIEF = SUMMARY_PROMPT


def ask(files, question, model, out_path):
    content = [file_block(f) for f in files] + [{"type": "text", "text": question}]
    text = call(model, content, task=f"ask {os.path.basename(files[0]) if files else ''}", max_tokens=16000,
                effort="medium")
    if out_path:
        open(out_path, "w", encoding="utf-8").write(text)
        print(f"wrote {out_path}")
    else:
        print(text)
    print(f"\n(total spent ${spent():.3f} of ${float(env('CLAUDE_BUDGET_USD', '100')):.2f})", file=sys.stderr)


if __name__ == "__main__":
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    cmd = args[0]
    if cmd == "cost":
        rows = [json.loads(l) for l in open(USAGE_LOG, encoding="utf-8")] if os.path.exists(USAGE_LOG) else []
        by = {}
        for r in rows:
            by[r["model"]] = by.get(r["model"], 0) + r["usd"]
        for m, v in by.items():
            print(f"{m}: ${v:.3f}")
        print(f"total ${spent():.3f} of ${float(env('CLAUDE_BUDGET_USD', '100')):.2f}, {len(rows)} calls")
    elif cmd == "sheets":
        for vid in args[1:] or sorted(os.listdir(os.path.join(REFERENCE, "youtube"))):
            sheets(vid, model_id(opts.get("model", "haiku")))
    elif cmd == "ask":
        q = None
        if "-q" in args:
            i = args.index("-q")
            q, args = args[i + 1], args[:i] + args[i + 2:]
        if not q:
            raise SystemExit('ask needs -q "question"')
        ask(args[1:], q, model_id(opts.get("model", "haiku")), opts.get("out"))
    else:
        raise SystemExit(__doc__)
