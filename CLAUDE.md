# Vlog-job

Learning travel-vlog editing style (Elena Taber, apinvy). Analysis: `docs/style-analysis.md`. Tools: see README.md.

Workflow for a new channel/video: `/learn-vlog <link>` (`.claude/skills/learn-vlog/SKILL.md`).

## Split of work: API key reads, Pro plan analyses
- The API key runs **Haiku 5.5 only** (script blocks Sonnet/Opus), for bulk reading: contact sheets, OCR, tagging.
  `py tools/claude_read.py sheets <id>` writes `reference/youtube/<id>/claude_visual_log.md` (text, one line per shot).
- **Analysis, style guides and synthesis are done in this Claude Code session (Pro plan)** from that log +
  `report.md` + Gemini notes. Do not send analysis tasks to the API.
- Do not Read contact sheets (`sheets/*.jpg`) one by one in the session; open single frames only to verify a claim.
- `py tools/claude_read.py cost` shows API spend (budget in `.env`, enforced).
- `ANTHROPIC_API_KEY` lives only in `.env`. Never export it as a shell/system variable: Claude Code would then
  bill the API instead of the Pro plan.

## Gemini (audio)
- Gemini hears music/SFX; Claude cannot (Claude API takes text, images, PDF only).
- Free tier: 20 requests/day/model per Google Cloud project; keys `GEMINI_API_KEY`, `_2`, `_3`... rotate automatically.
- `sh tools/run_gemini_all.sh` is safe to rerun: finished 8-minute chunks are cached.

Reply to the user in Vietnamese.
