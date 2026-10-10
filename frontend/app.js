const API_URL = "http://127.0.0.1:8000/api/v1/measurements";
const MAX_BYTES = 25 * 1024 * 1024;

const fileInput = document.querySelector("#file");
const dropzone = document.querySelector("#dropzone");
const measureButton = document.querySelector("#measure");
const message = document.querySelector("#message");
const fileRow = document.querySelector("#file-row");
const results = document.querySelector("#results");
let selectedFile = null;
let latestResult = null;

function formatNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 3 });
}

function setMessage(text) {
  message.textContent = text;
}

function selectFile(file) {
  setMessage("");
  if (!file) return;
  const name = file.name.toLowerCase();
  if (!(name.endsWith(".geojson") || name.endsWith(".json") || name.endsWith(".zip"))) {
    setMessage("Choose a .geojson, .json, or Shapefile .zip file.");
    return;
  }
  if (file.size > MAX_BYTES) {
    setMessage("The file exceeds the 25 MB upload limit.");
    return;
  }
  selectedFile = file;
  document.querySelector("#file-title").textContent = file.name;
  document.querySelector("#file-description").textContent = "Ready to process · " + (file.size / 1024).toFixed(1) + " KB";
  document.querySelector("#selected-name").textContent = file.name;
  document.querySelector("#selected-size").textContent = (file.size / 1024).toFixed(1) + " KB";
  fileRow.hidden = false;
  measureButton.disabled = false;
}

fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));
document.querySelector("#remove-file").addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  fileRow.hidden = true;
  measureButton.disabled = true;
  document.querySelector("#file-title").innerHTML = 'Drop your file here or <span>browse</span>';
  document.querySelector("#file-description").textContent = ".geojson or .zip · Maximum file size 25 MB";
  setMessage("");
});
["dragenter", "dragover"].forEach(eventName => dropzone.addEventListener(eventName, event => {
  event.preventDefault();
  dropzone.classList.add("dragging");
}));
["dragleave", "drop"].forEach(eventName => dropzone.addEventListener(eventName, event => {
  event.preventDefault();
  dropzone.classList.remove("dragging");
}));
dropzone.addEventListener("drop", event => {
  const file = event.dataTransfer.files[0];
  selectFile(file);
});

measureButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  const formData = new FormData();
  formData.append("file", selectedFile);
  measureButton.disabled = true;
  measureButton.textContent = "Processing…";
  setMessage("");
  try {
    const response = await fetch(API_URL, { method: "POST", body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const errorMessage = data?.error?.message || data?.detail || `Request failed (${response.status})`;
      throw new Error(typeof errorMessage === "string" ? errorMessage : JSON.stringify(errorMessage));
    }
    latestResult = data;
    showResults(data);
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    const isNetworkError = error instanceof TypeError;
    setMessage(isNetworkError
      ? "Could not connect to the API. Start the backend at http://127.0.0.1:8000 and check CORS settings."
      : error.message);
  } finally {
    measureButton.disabled = !selectedFile;
    measureButton.innerHTML = 'Calculate measurements <span>→</span>';
  }
});

function showResults(data) {
  document.querySelector("#area").textContent = formatNumber(data.total_area_m2);
  document.querySelector("#length").textContent = formatNumber(data.total_length_m);
  document.querySelector("#count").textContent = formatNumber(data.feature_count);
  document.querySelector("#result-filename").textContent = data.filename ?? "—";
  document.querySelector("#crs").textContent = data.source_crs ?? "—";
  document.querySelector("#method").textContent = data.measurement_method ?? "—";
  document.querySelector("#types").textContent = Object.entries(data.geometry_type_counts || {})
    .map(([type, count]) => `${type}: ${count}`).join(", ") || "—";
  document.querySelector("#bounds").textContent = Array.isArray(data.bounds)
    ? data.bounds.map(formatNumber).join(", ") : "—";

  const tbody = document.querySelector("#feature-rows");
  tbody.replaceChildren();
  (data.features || []).forEach(feature => {
    const row = document.createElement("tr");
    const values = [
      feature.feature_index ?? "—",
      feature.geometry_type ?? "—",
      formatNumber(feature.area_m2),
      formatNumber(feature.length_m),
      JSON.stringify(feature.properties ?? {})
    ];
    values.forEach(value => {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      row.appendChild(cell);
    });
    tbody.appendChild(row);
  });
}
document.querySelector("#download").addEventListener("click", () => {
  if (!latestResult) return;
  const blob = new Blob([JSON.stringify(latestResult, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "aereo-measurement-results.json";
  link.click();
  URL.revokeObjectURL(url);
});
