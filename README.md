# Spotlight Studio

Turn a short brief into a marketing video with an automatic voiceover.
Original code, no affiliation with any third-party studio product.

```
brief -> script (scenes) -> voiceover -> rendered MP4
```

## Run

Requires Python 3.11+ and `ffmpeg`.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # optional; defaults work offline
python -m studio          # http://127.0.0.1:8000
```

Or `docker build -t studio . && docker run -p 8000:8000 -v studio-data:/data studio`.

## What is real and what is a placeholder

| Stage  | Default    | Notes |
| ------ | ---------- | ----- |
| Script | `template` | Deterministic, offline. Splits your brief into scenes with a hook and call to action. No invented claims. |
| Voice  | `mock`     | Silence timed to the script, so the pipeline runs with no key. Set `VOICE_PROVIDER=elevenlabs` plus `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` for real speech. |
| Video  | `cards`    | Offline ffmpeg renderer: fade-in caption cards synced to the voiceover. It is **not** a generative-video model. |

Generative video and LLM scriptwriting are not included. Add them by implementing
the `VideoProvider` / `ScriptWriter` protocols in `studio/providers/base.py` and
registering them in `studio/providers/__init__.py`.

## Limits

There is no built-in cap by default (`MAX_JOBS_PER_DAY=0`), so you can queue as many
videos as you like. Real providers bill your own account per use, so set
`MAX_JOBS_PER_DAY` and `MAX_CONCURRENT_JOBS` to match your budget.

## API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/jobs` | Create a video job (`brief`, `tone`, `aspect`, `duration_s`, `voice`, optional `script`) |
| GET | `/api/jobs`, `/api/jobs/{id}` | List jobs / poll status |
| DELETE | `/api/jobs/{id}` | Delete a job and its files |
| POST | `/api/script` | Preview the script for a brief |
| GET | `/media/{id}/video.mp4` | Download the video |

## Develop

```bash
pip install -r requirements-dev.txt
ruff check . && pytest
```
