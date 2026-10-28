// Spotlight Studio (free): everything runs in the browser. No server, no API keys.
(() => {
  "use strict";

  const WORDS_PER_SECOND = 2.5;
  const FPS = 30;
  const PALETTE = ["#0f172a", "#7c2d12", "#134e4a", "#4c1d95", "#831843", "#1e3a8a"];
  const HOOKS = {
    energetic: "Stop scrolling!",
    professional: "Here is what you need to know.",
    friendly: "Hey, quick question for you.",
    luxury: "Introducing something extraordinary.",
  };
  const CTAS = {
    energetic: "Grab yours today!",
    professional: "Get started today.",
    friendly: "Give it a try, you will love it.",
    luxury: "Experience it for yourself.",
  };
  const ASPECTS = { "9:16": [720, 1280, 14], "1:1": [720, 720, 22], "16:9": [1280, 720, 34] };

  const $ = (id) => document.getElementById(id);
  const els = {
    form: $("form"), brief: $("brief"), tone: $("tone"), aspect: $("aspect"),
    duration: $("duration"), voice: $("voice"), preview: $("preview"),
    status: $("status"), error: $("error"), canvas: $("canvas"), player: $("player"),
    empty: $("empty"), downloads: $("downloads"), download: $("download"),
  };

  // Turns a brief into hook, one scene per sentence, and a call to action.
  function writeScript(brief, tone, durationS) {
    const parts = brief
      .split(/(?<=[.!?])\s+|\n+|;/)
      .map((p) => p.trim())
      .filter(Boolean)
      .flatMap((p) => (p.split(/\s+/).length > 14 ? p.split(",").map((c) => c.trim()).filter(Boolean) : [p]));
    const subject = (parts[0] || brief).replace(/[.!?\s]+$/, "");
    const budget = Math.floor(durationS * WORDS_PER_SECOND);
    const scenes = [{ caption: HOOKS[tone], narration: HOOKS[tone] }];
    let used = HOOKS[tone].split(" ").length + CTAS[tone].split(" ").length;
    for (const point of parts) {
      const words = point.split(/\s+/).length;
      if (used + words > budget && scenes.length > 1) break;
      scenes.push({ caption: point.replace(/[.!?]+$/, ""), narration: point });
      used += words;
    }
    scenes.push({ caption: CTAS[tone], narration: CTAS[tone] });
    return { title: subject.slice(0, 60), scenes };
  }

  // Splits the text into lines that fit the frame width (approximate, by characters).
  function wrap(text, maxChars) {
    const lines = [];
    let line = "";
    for (const word of text.split(/\s+/)) {
      if (line && (line + " " + word).length > maxChars) {
        lines.push(line);
        line = word;
      } else {
        line = line ? line + " " + word : word;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  function drawCard(ctx, width, height, color, lines, alpha) {
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, width, height);
    const size = Math.round(height / 18);
    ctx.font = `bold ${size}px system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = `rgba(255,255,255,${alpha})`;
    const lineHeight = size * 1.3;
    const top = height / 2 - ((lines.length - 1) * lineHeight) / 2;
    lines.forEach((l, i) => ctx.fillText(l, width / 2, top + i * lineHeight));
  }

  // Scene durations proportional to narration length, summing to the total.
  function sceneDurations(scenes, total) {
    const weights = scenes.map((s) => Math.max(1, s.narration.split(/\s+/).length));
    const sum = weights.reduce((a, b) => a + b, 0);
    return weights.map((w) => Math.max(0.8, (total * w) / sum));
  }

  function setStatus(text) { els.status.textContent = text; }
  function setError(text) { els.error.textContent = text || ""; }

  function pickVoices() {
    const voices = speechSynthesis.getVoices().filter((v) => v.lang.startsWith("en") || v.lang);
    els.voice.replaceChildren(
      new Option("Default", ""),
      ...voices.map((v) => new Option(`${v.name} (${v.lang})`, v.name)),
    );
  }
  if ("speechSynthesis" in window) {
    pickVoices();
    speechSynthesis.onvoiceschanged = pickVoices;
  } else {
    els.voice.replaceChildren(new Option("Not supported in this browser", ""));
    els.voice.disabled = true;
    els.preview.disabled = true;
  }

  function readInput() {
    const brief = els.brief.value.trim();
    if (brief.length < 3) throw new Error("Write a brief of at least 3 characters.");
    const duration = Number(els.duration.value);
    if (!(duration >= 5 && duration <= 60)) throw new Error("Length must be between 5 and 60 seconds.");
    return { brief, tone: els.tone.value, aspect: els.aspect.value, duration };
  }

  // Records the caption cards to a WebM file in real time.
  async function renderVideo(script, total, aspect) {
    const [width, height, wrapAt] = ASPECTS[aspect];
    const canvas = els.canvas;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    const durations = sceneDurations(script.scenes, total);
    const stream = canvas.captureStream(FPS);
    const mime = ["video/webm;codecs=vp9", "video/webm"].find((m) => MediaRecorder.isTypeSupported(m));
    if (!mime) throw new Error("This browser cannot record video. Try Chrome, Edge or Firefox.");
    const recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 3_000_000 });
    const chunks = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const done = new Promise((resolve) => (recorder.onstop = resolve));

    recorder.start();
    for (let i = 0; i < script.scenes.length; i++) {
      const lines = wrap(script.scenes[i].caption, wrapAt);
      const color = PALETTE[i % PALETTE.length];
      const end = performance.now() + durations[i] * 1000;
      setStatus(`Rendering scene ${i + 1} of ${script.scenes.length}…`);
      while (performance.now() < end) {
        const fade = Math.min(1, (performance.now() - (end - durations[i] * 1000)) / 400);
        drawCard(ctx, width, height, color, lines, fade);
        await new Promise((r) => setTimeout(r, 1000 / FPS));
      }
    }
    recorder.stop();
    await done;
    return new Blob(chunks, { type: "video/webm" });
  }

  // Speaks each scene's narration while the captions play, so the preview has a voice.
  function previewWithVoice(script, total, aspect) {
    const [width, height, wrapAt] = ASPECTS[aspect];
    const canvas = els.canvas;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    const durations = sceneDurations(script.scenes, total);
    const voiceName = els.voice.value;
    const voice = speechSynthesis.getVoices().find((v) => v.name === voiceName);
    speechSynthesis.cancel();
    return new Promise((resolve) => {
      let index = 0;
      const speakNext = () => {
        if (index >= script.scenes.length) return resolve();
        const scene = script.scenes[index];
        const u = new SpeechSynthesisUtterance(scene.narration);
        if (voice) u.voice = voice;
        u.rate = 1.05;
        u.onend = () => { index++; speakNext(); };
        u.onerror = () => { index++; speakNext(); };
        speechSynthesis.speak(u);
      };
      // Draw captions on a timer that matches the scene durations.
      let sceneIdx = 0;
      let sceneEnd = 0;
      const draw = () => {
        const now = performance.now();
        if (sceneIdx >= script.scenes.length) return;
        if (now >= sceneEnd) {
          if (sceneEnd !== 0) sceneIdx++;
          if (sceneIdx >= script.scenes.length) return;
          sceneEnd = now + durations[sceneIdx] * 1000;
        }
        const lines = wrap(script.scenes[sceneIdx].caption, wrapAt);
        drawCard(ctx, width, height, PALETTE[sceneIdx % PALETTE.length], lines, 1);
        requestAnimationFrame(draw);
      };
      canvas.hidden = false;
      els.player.hidden = true;
      els.empty.hidden = true;
      speakNext();
      draw();
      const total_ms = durations.reduce((a, b) => a + b, 0) * 1000 + 300;
      setTimeout(() => { speechSynthesis.cancel(); resolve(); }, total_ms);
    });
  }

  els.preview.onclick = async () => {
    setError("");
    try {
      const input = readInput();
      const script = writeScript(input.brief, input.tone, input.duration);
      els.preview.disabled = true;
      setStatus("Playing preview with voice…");
      await previewWithVoice(script, input.duration, input.aspect);
      setStatus("Preview finished.");
    } catch (err) {
      setError(err.message);
    } finally {
      els.preview.disabled = false;
    }
  };

  els.form.onsubmit = async (event) => {
    event.preventDefault();
    setError("");
    const submit = event.submitter;
    submit.disabled = true;
    try {
      const input = readInput();
      const script = writeScript(input.brief, input.tone, input.duration);
      if (els.download.dataset.url) URL.revokeObjectURL(els.download.dataset.url);
      const blob = await renderVideo(script, input.duration, input.aspect);
      const url = URL.createObjectURL(blob);
      els.download.href = url;
      els.download.dataset.url = url;
      els.player.src = url;
      els.canvas.hidden = true;
      els.player.hidden = false;
      els.empty.hidden = true;
      els.downloads.hidden = false;
      setStatus(`Done: "${script.title}", ${script.scenes.length} scenes.`);
    } catch (err) {
      setError(err.message);
      setStatus("");
    } finally {
      submit.disabled = false;
    }
  };
})();
