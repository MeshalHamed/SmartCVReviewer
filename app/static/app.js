const form = document.querySelector("#reviewForm");
const fileInput = document.querySelector("#cvFile");
const textInput = document.querySelector("#cvText");
const dropZone = document.querySelector("#dropZone");
const fileLabel = document.querySelector("#fileLabel");
const fileHint = document.querySelector("#fileHint");
const removeFile = document.querySelector("#removeFile");
const submitBtn = document.querySelector("#submitBtn");
const formNote = document.querySelector("#formNote");
const results = document.querySelector("#results");
const apiStatus = document.querySelector("#apiStatus");

const isArabic = (text = "") => /[\u0600-\u06ff]/.test(text);

function syncInputs() {
  const hasFile = fileInput.files.length > 0;
  const hasText = textInput.value.trim().length > 0;

  textInput.disabled = hasFile;
  dropZone.classList.toggle("disabled", hasText);
  fileInput.disabled = hasText;
  removeFile.classList.toggle("hidden", !hasFile);

  if (hasFile) {
    fileLabel.textContent = fileInput.files[0].name;
    fileHint.textContent = "File selected. Remove it to paste text.";
    formNote.textContent = "Text input is disabled while a file is selected.";
  } else if (hasText) {
    fileLabel.textContent = "Upload disabled";
    fileHint.textContent = "Clear the text box to upload a file.";
    formNote.textContent = "File upload is disabled while text is present.";
  } else {
    fileLabel.textContent = "Choose PDF or TXT";
    fileHint.textContent = "Max 6 MB. Remove it to enable text input.";
    formNote.textContent = "One input method can be active at a time.";
  }
}

function setLoading() {
  results.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <strong>Reviewing the CV with retrieved evidence...</strong>
    </div>
  `;
}

function list(items = []) {
  if (!items.length) return "<p>No clear evidence found.</p>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderReview(data) {
  const rtl = data.language === "Arabic" || isArabic(data.executive_summary);
  const score = Math.max(0, Math.min(100, Number(data.ats_score || 0)));
  const downloadUrl = data.review_id ? `/api/reviews/${encodeURIComponent(data.review_id)}/modified-cv.pdf` : "";
  results.dir = rtl ? "rtl" : "ltr";
  results.innerHTML = `
    <div class="score-row">
      <div>
        <p class="eyebrow">${escapeHtml(data.language)} Review</p>
        <h2>CV Review</h2>
      </div>
      <div class="score" style="--score: ${score}%">${score}</div>
    </div>
    <p class="summary">${escapeHtml(data.executive_summary)}</p>
    ${
      downloadUrl
        ? `<a class="download-btn" href="${downloadUrl}" target="_blank" rel="noopener">${rtl ? "تحميل السيرة الذاتية المحسنة PDF" : "Download Optimized CV PDF"}</a>`
        : ""
    }

    <div class="grid">
      <article class="card">
        <h3>${rtl ? "نقاط القوة" : "Strengths"}</h3>
        ${list(data.strengths)}
      </article>
      <article class="card">
        <h3>${rtl ? "نقاط الضعف" : "Weaknesses"}</h3>
        ${list(data.weaknesses)}
      </article>
      <article class="card">
        <h3>${rtl ? "تحسينات مقترحة" : "Improvements"}</h3>
        ${list(data.improvements)}
      </article>
      <article class="card">
        <h3>${rtl ? "كلمات مفتاحية ناقصة" : "Missing Keywords"}</h3>
        ${list(data.missing_keywords)}
      </article>
      <article class="card">
        <h3>${rtl ? "وظائف مناسبة" : "Recommended Roles"}</h3>
        <div class="roles">
          ${(data.recommended_roles || []).map(renderRole).join("") || "<p>No roles returned.</p>"}
        </div>
      </article>
      <article class="card">
        <h3>${rtl ? "الخطوات التالية" : "Next Steps"}</h3>
        ${list(data.next_steps)}
      </article>
    </div>
  `;
}

function renderRole(role) {
  const keywords = (role.keywords || []).map((keyword) => `<span class="tag">${escapeHtml(keyword)}</span>`).join("");
  return `
    <div class="role">
      <strong>
        <span>${escapeHtml(role.title)}</span>
        <span>${Number(role.fit_score || 0)}%</span>
      </strong>
      <p>${escapeHtml(role.why)}</p>
      <div class="tags">${keywords}</div>
    </div>
  `;
}

function renderError(message) {
  results.dir = "ltr";
  results.innerHTML = `
    <article class="card error">
      <h3>Review failed</h3>
      <p>${escapeHtml(message)}</p>
    </article>
  `;
}

fileInput.addEventListener("change", syncInputs);
textInput.addEventListener("input", syncInputs);
removeFile.addEventListener("click", () => {
  fileInput.value = "";
  syncInputs();
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drag");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, () => dropZone.classList.remove("drag"));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData();

  if (fileInput.files.length > 0) {
    formData.append("file", fileInput.files[0]);
  } else if (textInput.value.trim()) {
    formData.append("cv_text", textInput.value.trim());
  } else {
    renderError("Upload a CV file or paste CV text.");
    return;
  }

  submitBtn.disabled = true;
  setLoading();

  try {
    const response = await fetch("/api/review", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unknown error");
    renderReview(data);
  } catch (error) {
    renderError(error.message);
  } finally {
    submitBtn.disabled = false;
  }
});

async function checkApi() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("bad");
    apiStatus.textContent = "API ready";
    apiStatus.classList.add("ok");
  } catch {
    apiStatus.textContent = "API offline";
    apiStatus.classList.add("bad");
  }
}

syncInputs();
checkApi();
