import dataclasses

import httpx
import pytest

from studio.api import create_app

BRIEF = "Our bottle keeps drinks cold for 24 hours. It fits every cup holder. Order today."


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_job_runs_to_a_playable_video(app, client, settings):
    resp = await client.post("/api/jobs", json={"brief": BRIEF, "duration_s": 10, "aspect": "16:9"})
    assert resp.status_code == 202
    job_id = resp.json()["id"]
    await app.state.pipeline.drain()

    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "done", job["error"]
    assert job["script"]["scenes"][-1]["narration"]
    assert job["video_url"] and job["audio_url"]

    video = await client.get(job["video_url"])
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"
    assert video.content[4:8] == b"ftyp"


async def test_custom_script_skips_writer(app, client):
    script = {"title": "t", "scenes": [{"caption": "Hello", "narration": "Hello there friend"}]}
    resp = await client.post("/api/jobs", json={"brief": "x y z", "script": script})
    await app.state.pipeline.drain()
    job = (await client.get(f"/api/jobs/{resp.json()['id']}")).json()
    assert job["status"] == "done"
    assert job["script"]["title"] == "t"


async def test_daily_cap_returns_429(settings):
    capped = create_app(dataclasses.replace(settings, max_jobs_per_day=1))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=capped), base_url="http://t") as c:
        assert (await c.post("/api/jobs", json={"brief": BRIEF})).status_code == 202
        assert (await c.post("/api/jobs", json={"brief": BRIEF})).status_code == 429
        await capped.state.pipeline.drain()


async def test_validation_and_missing_job(client):
    assert (await client.post("/api/jobs", json={"brief": "x"})).status_code == 422
    assert (await client.get("/api/jobs/" + "0" * 32)).status_code == 404
    assert (await client.delete("/api/jobs/not-a-job-id")).status_code == 404


async def test_delete_removes_media(app, client, settings):
    job_id = (await client.post("/api/jobs", json={"brief": BRIEF})).json()["id"]
    await app.state.pipeline.drain()
    assert (await client.delete(f"/api/jobs/{job_id}")).status_code == 204
    assert not (settings.media_dir / job_id).exists()
    assert (await client.get(f"/api/jobs/{job_id}")).status_code == 404
