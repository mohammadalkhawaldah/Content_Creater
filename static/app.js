async function postForm(form) {
  const data = new FormData(form);
  const resp = await fetch("/api/jobs", { method: "POST", body: data });
  if (!resp.ok) {
    const err = await resp.text();
    alert(err);
    return;
  }
  const payload = await resp.json();
  window.location.href = `/jobs/${payload.id}`;
}

async function pollJob(jobId) {
  const statusEl = document.getElementById("status");
  const folderEl = document.getElementById("folder-path");
  const downloadEl = document.getElementById("download-link");

  const resp = await fetch(`/api/jobs/${jobId}`);
  if (!resp.ok) return;
  const data = await resp.json();
  statusEl.textContent = `${data.status} • ${data.current_step || "waiting"} • ${data.percent}%`;
  folderEl.textContent = `Folder: ${data.job_path}`;
  downloadEl.href = `/api/jobs/${jobId}/download`;

  if (data.status === "succeeded") {
    await loadResults(jobId);
  } else if (data.status === "failed") {
    statusEl.textContent = `failed • ${data.error || "unknown error"}`;
  } else {
    setTimeout(() => pollJob(jobId), 3000);
  }
}

function renderPosts(drafts) {
  const tabs = document.getElementById("posts-tabs");
  const content = document.getElementById("posts-content");
  if (!tabs || !content) return;
  const categories = [
    ["linkedin", "LinkedIn"],
    ["x", "X"],
    ["ig", "Instagram"],
    ["blog", "Blog"],
  ];
  tabs.innerHTML = "";
  content.innerHTML = "";
  categories.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.onclick = () => {
      content.innerHTML = "";
      (drafts[key] || []).forEach((item) => {
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = `<strong>${item.id || ""}</strong><pre>${JSON.stringify(item, null, 2)}</pre>`;
        content.appendChild(div);
      });
    };
    tabs.appendChild(btn);
  });
}

function renderPosters(posters) {
  const container = document.getElementById("posters-content");
  if (!container) return;
  container.innerHTML = "";
  Object.values(posters || {}).flat().forEach((item) => {
    const img = document.createElement("img");
    img.src = item.url;
    img.alt = item.name;
    img.onclick = () => window.open(item.url, "_blank");
    container.appendChild(img);
  });
}

function renderDocs(docs) {
  const list = document.getElementById("docs-list");
  if (!list) return;
  list.innerHTML = "";
  (docs || []).forEach((doc) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = doc.url;
    a.textContent = doc.name;
    a.target = "_blank";
    li.appendChild(a);
    list.appendChild(li);
  });
}

async function loadResults(jobId) {
  const resp = await fetch(`/api/jobs/${jobId}/results`);
  if (!resp.ok) return;
  const data = await resp.json();
  renderPosts(data.drafts);
  renderPosters(data.posters);
  renderDocs(data.docs);
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("job-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      postForm(form);
    });
  }
  if (window.JOB_ID) {
    document.getElementById("job-id").textContent = window.JOB_ID;
    pollJob(window.JOB_ID);
  }
});
