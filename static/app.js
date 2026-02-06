let currentUpload = null;

function postForm(form) {
  const data = new FormData(form);
  const progress = document.getElementById("upload-progress");
  const label = document.getElementById("upload-label");
  const cancelBtn = document.getElementById("upload-cancel");
  const submitBtn = document.getElementById("generate-btn");
  const errorBox = document.getElementById("form-error");

  progress.value = 0;
  label.textContent = "0%";
  cancelBtn.disabled = false;
  if (submitBtn) submitBtn.disabled = true;
  if (errorBox) errorBox.textContent = "";

  const xhr = new XMLHttpRequest();
  currentUpload = xhr;
  xhr.open("POST", "/api/jobs", true);
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      const percent = Math.round((event.loaded / event.total) * 100);
      progress.value = percent;
      label.textContent = `${percent}%`;
    }
  };
  xhr.onload = () => {
    cancelBtn.disabled = true;
    if (submitBtn) submitBtn.disabled = false;
    if (xhr.status >= 200 && xhr.status < 300) {
      const payload = JSON.parse(xhr.responseText);
      window.location.href = `/jobs/${payload.id}`;
    } else {
      if (errorBox) {
        errorBox.textContent = xhr.responseText || "Upload failed.";
      } else {
        alert(xhr.responseText || "Upload failed.");
      }
    }
  };
  xhr.onerror = () => {
    cancelBtn.disabled = true;
    if (submitBtn) submitBtn.disabled = false;
    if (errorBox) {
      errorBox.textContent = "Upload failed.";
    } else {
      alert("Upload failed.");
    }
  };
  xhr.onabort = () => {
    cancelBtn.disabled = true;
    if (submitBtn) submitBtn.disabled = false;
    label.textContent = "Canceled";
  };
  xhr.send(data);
}

async function pollJob(jobId, delayMs = 1000) {
  const statusEl = document.getElementById("status-text");
  const progressEl = document.getElementById("job-progress");
  const folderEl = document.getElementById("folder-path");
  const downloadEl = document.getElementById("download-link");

  const resp = await fetch(`/api/jobs/${jobId}`);
  if (!resp.ok) return;
  const data = await resp.json();
  if (statusEl) {
    statusEl.textContent = `${data.status} | ${data.current_step || "waiting"} | ${data.percent}%`;
  }
  if (progressEl) {
    progressEl.value = data.percent || 0;
  }
  folderEl.textContent = `Folder: ${data.job_path}`;
  downloadEl.href = `/api/jobs/${jobId}/download`;

  await loadResults(jobId);
  if (data.status === "failed" || data.status === "succeeded") {
    if (statusEl) {
      if (data.status === "failed") {
        statusEl.textContent = `failed | ${data.error || "unknown error"}`;
      }
    }
    return;
  }

  const nextDelay = Math.min(delayMs * 2, 5000);
  setTimeout(() => pollJob(jobId, nextDelay), delayMs);
}

function clearResults() {
  const summaryEl = document.getElementById("summary-text");
  if (summaryEl) {
    summaryEl.textContent = "Waiting for summary...";
  }
  const postsTabs = document.getElementById("posts-tabs");
  const postsContent = document.getElementById("posts-content");
  const posters = document.getElementById("posters-content");
  const docs = document.getElementById("docs-list");
  if (postsTabs) postsTabs.innerHTML = "";
  if (postsContent) postsContent.innerHTML = "";
  if (posters) posters.innerHTML = "";
  if (docs) docs.innerHTML = "";
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
  const total =
    (drafts?.linkedin?.length || 0) +
    (drafts?.x?.length || 0) +
    (drafts?.ig?.length || 0) +
    (drafts?.blog?.length || 0);
  if (!total) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = "No posts yet.";
    content.appendChild(empty);
  }
  categories.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.onclick = () => {
      content.innerHTML = "";
      (drafts[key] || []).forEach((item) => {
        const div = document.createElement("div");
        div.className = "card";
        const header = document.createElement("strong");
        header.textContent = item.id || "";
        const body = document.createElement("div");
        body.className = "post-text";
        body.textContent = JSON.stringify(item, null, 2);
        div.appendChild(header);
        div.appendChild(body);
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
  const summaryEl = document.getElementById("summary-text");
  if (summaryEl && data.summary) {
    summaryEl.textContent = data.summary;
    summaryEl.classList.remove("muted");
  }
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
    const generateBtn = document.getElementById("generate-btn");
    if (generateBtn) {
      generateBtn.addEventListener("click", () => postForm(form));
    }
    const cancelBtn = document.getElementById("upload-cancel");
    cancelBtn.addEventListener("click", () => {
      if (currentUpload) {
        currentUpload.abort();
        currentUpload = null;
      }
    });
  }
  if (window.JOB_ID) {
    document.getElementById("job-id").textContent = window.JOB_ID;
    clearResults();
    pollJob(window.JOB_ID);
  }
});
