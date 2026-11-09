import json, sys
sys.path.insert(0, "tools")
from gemini import generate_json, video_part
v = sys.argv[1]
prompt = """You are QA for a vlog edit (3.5 min). Listen carefully and watch. Return JSON:
{"cut_words":[{"t":"m:ss.s","issue":"word clipped / sentence cut mid-word / abrupt audio jump"}],
 "music_balance":[{"t":"m:ss.s","issue":"music too loud over speech / too quiet in montage"}],
 "copyrighted_song":[{"t":"m:ss.s","what":"any recognisable commercial song or lyrics audible"}],
 "sfx":[{"t":"m:ss.s","what":"sfx heard and whether it fits"}],
 "pacing":["short notes on pacing, dead air, repetition"],
 "overall":"2-3 sentences"}
Only list real problems; timestamps as strings."""
print(json.dumps(generate_json([video_part(v), {"text": prompt}], timeout=600), ensure_ascii=False, indent=1))
