"""Accurate word timings (start AND end) with faster-whisper. The audio is decoded by ffmpeg and passed as an
array, which sidesteps the broken PyAV file reader on this machine."""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
src = sys.argv[1]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(raw, np.float32)
model = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False, beam_size=5)
words = [[round(w.start, 2), w.word.strip(), round(w.end, 2)] for s in segs for w in s.words]
json.dump(words, open(sys.argv[2], "w"), indent=0)
print(len(words), "words")
