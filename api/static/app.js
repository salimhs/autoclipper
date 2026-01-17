// Minimal, elegant dashboard logic (no frameworks).
// Talks to the FastAPI backend endpoints in api/job_controller.py.

const $ = (id) => document.getElementById(id);

const apiStatus = $("apiStatus");
const refreshBtn = $("refreshBtn");
const createJobBtn = $("createJobBtn");
const videoUrl = $("videoUrl");
const createError = $("createError");
const createSuccess = $("createSuccess");

const jobId = $("jobId");
const checkJobBtn = $("checkJobBtn");
const jobEmpty = $("jobEmpty");
const jobCard = $("jobCard");
const jobStatus = $("jobStatus");
const jobProgress = $("jobProgress");
const jobVideo = $("jobVideo");
const jobError = $("jobError");

const clips = $("clips");
const clipsEmpty = $("clipsEmpty");
const pollBtn = $("pollBtn");
const stopPollBtn = $("stopPollBtn");

let pollTimer = null;

function show(el) {
  el.classList.remove("hidden");
}

function hide(el) {
  el.classList.add("hidden");
}

function setPill(el, text, tone = "neutral") {
  el.textContent = text;
  el.className = "text-xs px-2 py-1 rounded-full border";
  if (tone === "good") el.className += " bg-emerald-50 border-emerald-200 text-emerald-800";
  else if (tone === "bad") el.className += " bg-red-50 border-red-200 text-red-800";
  else if (tone === "warn") el.className += " bg-amber-50 border-amber-200 text-amber-800";
  else el.className += " bg-neutral-50 border-neutral-200 text-neutral-800";
}

async function pingApi() {
  try {
    // We rely on /docs existing (FastAPI). If you disable docs, change to a real health endpoint.
    const res = await fetch("/docs", { method: "GET" });
    if (!res.ok) throw new Error("not ok");
    setPill(apiStatus, "API: online", "good");
  } catch {
    setPill(apiStatus, "API: offline", "bad");
  }
}

function formatClip(clip, idx) {
  // Clip schema can evolve; we render common fields defensively.
  const title = clip.title ?? clip.name ?? `Clip ${idx + 1}`;
  const url = clip.url ?? clip.link ?? "";
  const score = clip.score ?? clip.confidence ?? null;
  const reason = clip.reason ?? clip.note ?? null;

  const wrap = document.createElement("div");
  wrap.className = "rounded-2xl border bg-white p-4";

  const header = document.createElement("div");
  header.className = "flex items-start justify-between gap-2";

  const left = document.createElement("div");
  left.className = "space-y-1";
  const t = document.createElement("div");
  t.className = "font-semibold";
  t.textContent = title;
  const sub = document.createElement("div");
  sub.className = "text-xs text-neutral-600";
  sub.textContent = score != null ? `Score: ${score}` : "";
  left.appendChild(t);
  if (sub.textContent) left.appendChild(sub);

  const right = document.createElement("div");
  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.className = "text-sm text-blue-700 hover:underline";
    a.textContent = "Open";
    right.appendChild(a);
  }

  header.appendChild(left);
  header.appendChild(right);

  wrap.appendChild(header);

  if (reason) {
    const r = document.createElement("div");
    r.className = "mt-2 text-sm text-neutral-700";
    r.textContent = reason;
    wrap.appendChild(r);
  }

  return wrap;
}

function renderJob(job) {
  hide(jobEmpty);
  show(jobCard);
  hide(jobError);

  // Status
  const status = job.status ?? "unknown";
  const progress = job.progress ?? "";
  const tone = status === "completed" ? "good" : status === "failed" ? "bad" : status === "processing" ? "warn" : "neutral";
  setPill(jobStatus, status, tone);
  jobProgress.textContent = progress ? `(${progress})` : "";

  // Video URL
  jobVideo.textContent = job.video_url ?? "—";
  jobVideo.href = job.video_url ?? "#";

  // Clips
  clips.innerHTML = "";
  const list = Array.isArray(job.clips) ? job.clips : [];
  if (list.length === 0) {
    show(clipsEmpty);
  } else {
    hide(clipsEmpty);
    list.forEach((c, i) => clips.appendChild(formatClip(c, i)));
  }

  // Error
  if (job.error) {
    jobError.textContent = job.error;
    show(jobError);
  } else {
    hide(jobError);
  }
}

async function createJob() {
  hide(createError);
  hide(createSuccess);

  const url = videoUrl.value.trim();
  if (!url) {
    createError.textContent = "Please enter a video URL.";
    show(createError);
    return;
  }

  createJobBtn.disabled = true;
  createJobBtn.textContent = "Creating…";
  try {
    const res = await fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_url: url }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Failed to create job.");
    }

    jobId.value = data.job_id;
    createSuccess.textContent = `Job created: ${data.job_id}`;
    show(createSuccess);

    await loadJob(data.job_id);
  } catch (e) {
    createError.textContent = String(e.message || e);
    show(createError);
  } finally {
    createJobBtn.disabled = false;
    createJobBtn.textContent = "Create";
  }
}

async function loadJob(id) {
  const jid = (id ?? jobId.value).trim();
  if (!jid) return;

  try {
    const res = await fetch(`/jobs/${encodeURIComponent(jid)}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "Job not found.");
    }
    renderJob(data);
  } catch (e) {
    show(jobCard);
    hide(jobEmpty);
    jobError.textContent = String(e.message || e);
    show(jobError);
  }
}

function startPoll() {
  if (pollTimer) return;
  pollBtn.disabled = true;
  stopPollBtn.disabled = false;
  pollTimer = setInterval(() => loadJob(), 1500);
}

function stopPoll() {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
  pollBtn.disabled = false;
  stopPollBtn.disabled = true;
}

// Wire events
refreshBtn.addEventListener("click", () => {
  pingApi();
  if (jobId.value.trim()) loadJob();
});

createJobBtn.addEventListener("click", createJob);
checkJobBtn.addEventListener("click", () => loadJob());

pollBtn.addEventListener("click", startPoll);
stopPollBtn.addEventListener("click", stopPoll);

videoUrl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") createJob();
});

jobId.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadJob();
});

// Init
pingApi();
