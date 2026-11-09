import json, os, sys
sys.path.insert(0, "tools")
from gemini import audio_part, generate_json
d = "work/edit_test/music/clips"
names = sorted(f for f in os.listdir(d) if f.endswith(".mp3"))
parts = []
for n in names:
    parts += [{"text": f"Track: {n[:-4]}"}, audio_part(os.path.join(d, n))]
parts.append({"text": "For each track above (45s excerpt) return JSON list of {track, genre, bpm, mood, energy_1_10, "
              "instruments, has_vocals, fits: one of [cold_open_upbeat_jazz, lofi_bed_under_speech, acoustic_daytime, soft_ending]}. "
              "Context: a Vietnamese-style lifestyle vlog edit (lo-fi/jazz/acoustic beds, ducked under talking)."})
print(json.dumps(generate_json(parts, timeout=300), ensure_ascii=False, indent=1))
