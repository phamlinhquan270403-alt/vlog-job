#!/bin/sh
# Run the Gemini audio/edit pass on every video in reference/youtube/ (after GEMINI_API_KEY is in .env).
# One video at a time, 2 chunks in parallel: the free tier allows 5 requests/min per model.
# Finished chunks are cached in <id>/chunks/*.json, so rerunning after a quota error only redoes the rest.
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
for d in reference/youtube/*/; do
  id=$(basename "$d")
  [ -f "$d/report.md" ] || continue
  py tools/watch_video.py "$d/video.mp4" "$id" --gemini-only > "logs/gemini_$id.log" 2>&1
  echo "$id exit $?"
done
