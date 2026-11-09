"""YouTube json3 auto-captions -> word timings (start seconds, word) in words.json; print ranges for reading."""
import json, sys, glob
src = glob.glob("reference/youtube/MPZWJls31Vw/*.json3")[0]
words = []
for e in json.load(open(src, encoding="utf-8"))["events"]:
    t0 = e.get("tStartMs", 0)
    for s in e.get("segs", []):
        w = s.get("utf8", "").strip()
        if w and w != "\n":
            words.append([round((t0 + s.get("tOffsetMs", 0)) / 1000, 2), w])
json.dump(words, open("work/edit_test/words.json", "w"), indent=0)
for a, b in [tuple(map(float, r.split("-"))) for r in sys.argv[1:]]:
    line, start = [], None
    for t, w in words:
        if a <= t < b:
            if start is None or t - start > 6:
                if line: print(" ".join(line))
                line, start = [f"\n[{t:.2f}]"], t
            line.append(f"{w}")
    print(" ".join(line))
