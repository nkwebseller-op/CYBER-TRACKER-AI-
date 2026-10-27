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

## Providers

| Stage  | Default    | Real option |
| ------ | ---------- | ----------- |
| Script | `template` | none yet (deterministic, offline, adds no claims of its own) |
| Voice  | `mock`     | `VOICE_PROVIDER=elevenlabs` |
| Video  | `cards`    | `VIDEO_PROVIDER=replicate` |

The defaults need no keys: the voice is silence and the video is ffmpeg caption cards,
so you can try the whole flow for free.

**ElevenLabs voice.** Set `VOICE_PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, and
optionally `ELEVENLABS_VOICE_ID` as the default. The voice box in the UI lists the
voices on your account.

**AI video (Replicate).** Set `VIDEO_PROVIDER=replicate` and `REPLICATE_API_TOKEN`.
Each scene becomes one text-to-video clip (`google/veo-3.1-fast` by default). Clips are
trimmed or looped to the scene length, cropped to your format, captioned, and mixed with
the voiceover; the model's own audio is dropped. To use a different model, change
`REPLICATE_VIDEO_MODEL` and `REPLICATE_VIDEO_INPUT` together, because input names differ
per model (check its API tab). Costs are per clip, so a 20 second video is about 5 runs.
`REPLICATE_MAX_CLIPS` refuses oversized scripts before any money is spent.

> Both integrations were built against the providers' published API docs and tested with
> mocked HTTP. They have not been run against the live services, so try one short video
> first.

Other providers plug in through the protocols in `studio/providers/base.py`.

## Limits

There is no built-in cap by default (`MAX_JOBS_PER_DAY=0`), so you can queue as many
videos as you like. ElevenLabs and Replicate bill your own account per use, so set
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
