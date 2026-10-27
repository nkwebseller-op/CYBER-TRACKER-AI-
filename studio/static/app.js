const $ = (id) => document.getElementById(id);
const ACTIVE = new Set(["queued", "scripting", "voicing", "rendering"]);

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : "Invalid request";
    } catch { /* keep statusText */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function payload() {
  return {
    brief: $("brief").value.trim(),
    tone: $("tone").value,
    aspect: $("aspect").value,
    duration_s: Number($("duration").value),
    voice: $("voice").value.trim() || null,
  };
}

function renderJob(job) {
  const badge = el("span", { className: `badge ${job.status}` }, job.status);
  const title = job.script?.title || job.brief.slice(0, 60);
  const node = el("div", { className: "job" }, el("strong", {}, title), " ", badge);
  if (job.error) node.append(el("p", { className: "error" }, job.error));
  if (job.video_url) {
    node.append(el("video", { src: job.video_url, controls: true, preload: "metadata" }));
    node.append(el("div", { className: "job-actions" },
      el("a", { href: job.video_url, download: `${job.id}.mp4` }, "Download video"),
      job.audio_url ? el("a", { href: job.audio_url, download: `${job.id}-voice` }, "Download voiceover") : "",
    ));
  }
  const remove = el("button", { type: "button" }, "Delete");
  remove.onclick = async () => { await api(`/api/jobs/${job.id}`, { method: "DELETE" }); refresh(); };
  node.append(el("div", { className: "job-actions" }, remove));
  return node;
}

let timer;
async function refresh() {
  clearTimeout(timer);
  const [jobs, cfg] = await Promise.all([api("/api/jobs"), api("/api/config")]);
  $("jobs").replaceChildren(...(jobs.length ? jobs.map(renderJob) : [el("p", { className: "muted" }, "Nothing yet.")]));
  const cap = cfg.max_jobs_per_day ? `${cfg.jobs_today}/${cfg.max_jobs_per_day} today` : "no daily cap";
  $("status").textContent = `Script: ${cfg.script_provider} · Voice: ${cfg.voice_provider} · Video: ${cfg.video_provider} · ${cap}`;
  if (jobs.some((j) => ACTIVE.has(j.status))) timer = setTimeout(refresh, 2000);
}

$("form").onsubmit = async (event) => {
  event.preventDefault();
  $("error").textContent = "";
  const submit = event.submitter;
  submit.disabled = true;
  try {
    await api("/api/jobs", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload()) });
    await refresh();
  } catch (err) {
    $("error").textContent = err.message;
  } finally {
    submit.disabled = false;
  }
};

$("preview").onclick = async () => {
  $("error").textContent = "";
  const p = payload();
  try {
    const q = new URLSearchParams({ brief: p.brief, tone: p.tone, duration_s: p.duration_s });
    const script = await api(`/api/script?${q}`, { method: "POST" });
    $("script").hidden = false;
    $("script").textContent = script.scenes.map((s, i) => `${i + 1}. ${s.narration}`).join("\n");
  } catch (err) {
    $("error").textContent = err.message;
  }
};

async function loadVoices() {
  try {
    const voices = await api("/api/voices");
    $("voices").replaceChildren(...voices.map((v) => el("option", { value: v.id, label: v.name })));
  } catch { /* free-text voice id still works */ }
}

loadVoices();
refresh().catch((err) => { $("error").textContent = err.message; });
