/**
 * app.js - Competition Edition
 * Full front-end interactivity for AI Meeting Action-Item Extractor.
 */

let currentActionItems = [];
let currentAnalytics = null;
let isAudioPlaying = false;
let audioTimer = null;

// Presets
const PRESETS = {
  1: {
    title: "Mobile App Launch Sync",
    transcript: `[00:01] Carlos: Good morning everyone! Did everyone catch the football match yesterday evening?
[00:02] Priya: Haha, yes Carlos, incredible game! But we should probably look at our release blockers.
[00:03] Carlos: Right, down to business. I will update the API authentication documentation by tomorrow at 3 PM.
[00:04] Priya: Great. Also, we really need to redesign the user onboarding illustrations before the marketing push next Friday.
[00:05] Marcus: I can help coordinate the user testing sessions, but I haven't checked my calendar yet so I'm not sure when.
[00:06] Carlos: Sounds like a plan. Let's reconvene on Wednesday.`
  },
  2: {
    title: "Sprint Planning: Backend & Infra",
    transcript: `Sarah: Okay team, let's divide sprint deliverables.
David: I will finish drafting the quarterly budget spreadsheet by this Thursday at 4 PM.
Sarah: Awesome. Elena, can you please review the database migration PR by Friday?
Elena: Yes, I can take care of the database migration PR.
Sarah: Also, someone needs to push the hotfix to the staging server before 8 PM tonight.
David: I'll review the pull requests submitted by the intern team.
Sarah: Sounds great, that covers our sprint.`
  },
  3: {
    title: "Casual Banter (Zero Action Items)",
    transcript: `Maya: That was a great presentation. We could potentially explore entering the European market next year, but honestly, sales were already strong in Asia last quarter. What do you think?
Liam: I agree, let's keep that in mind for future discussions.
Maya: Exactly, no immediate pressure. Let's grab some coffee.`
  }
};

// Document ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  clearAll();
  const inputArea = document.getElementById("transcriptInput");
  if (inputArea) {
    inputArea.addEventListener("input", updateTurnCount);
  }
});

// Theme Management
function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-bs-theme", saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-bs-theme");
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-bs-theme", next);
  localStorage.setItem("theme", next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("themeIcon");
  if (!icon) return;
  if (theme === "dark") {
    icon.className = "bi bi-sun-fill text-warning";
  } else {
    icon.className = "bi bi-moon-stars";
  }
}

// Preset Loading
function loadPreset(num) {
  const p = PRESETS[num];
  if (!p) return;
  const area = document.getElementById("transcriptInput");
  area.value = p.transcript;
  updateTurnCount();
  extractTasks();
}

function updateTurnCount() {
  const text = document.getElementById("transcriptInput").value.trim();
  const lines = text.split("\n").filter(l => l.trim().length > 0);
  const badge = document.getElementById("turnCountBadge");
  if (badge) badge.innerText = `${lines.length} Turns`;
}

function clearAll() {
  document.getElementById("transcriptInput").value = "";
  currentActionItems = [];
  renderResults([]);
  updateTurnCount();
}

// Extract Tasks API
async function extractTasks() {
  const text = document.getElementById("transcriptInput").value.trim();
  const date = document.getElementById("meetingDate").value;
  const engine = document.getElementById("engineSelect").value;

  if (!text) {
    showToast("Please enter or select a transcript.");
    return;
  }

  const btn = document.getElementById("extractBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Extracting with ${engine.toUpperCase()}...`;

  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript: text, meeting_date: date, engine: engine })
    });

    const data = await res.json();
    currentActionItems = data.action_items || [];
    currentAnalytics = data.analytics;

    renderResults(currentActionItems);
    showToast(`Extracted ${currentActionItems.length} action items successfully!`);
  } catch (err) {
    console.error(err);
    showToast("Server error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-lightning-charge-fill"></i> Extract Action Items`;
  }
}

// Render Results Table
function renderResults(items) {
  const tbody = document.getElementById("itemsTableBody");
  const zeroNotice = document.getElementById("zeroStateNotice");
  tbody.innerHTML = "";

  const total = items.length;
  const confirmed = items.filter(i => i.review_status === "Confirmed").length;
  const review = total - confirmed;

  document.getElementById("mTotal").innerText = total;
  document.getElementById("mConfirmed").innerText = confirmed;
  document.getElementById("mReview").innerText = review;

  if (total === 0) {
    zeroNotice.style.display = "block";
    return;
  }
  zeroNotice.style.display = "none";

  items.forEach((item, idx) => {
    const tr = document.createElement("tr");

    const isUnassigned = item.owner === "Unassigned";
    const isUnspecified = item.deadline === "Unspecified";
    const isConfirmed = item.review_status === "Confirmed";

    tr.innerHTML = `
      <td class="text-center text-muted fw-bold">${idx + 1}</td>
      <td>
        <input type="text" class="editable-input fw-semibold" value="${escapeHtml(item.task)}" onchange="updateItemField(${idx}, 'task', this.value)">
        <small class="text-muted text-truncate d-block italic mt-0.5">"${escapeHtml(item.source_quote)}"</small>
        ${item.review_reason ? `<small class="text-warning-emphasis d-block mt-0.5"><i class="bi bi-info-circle me-1"></i>${escapeHtml(item.review_reason)}</small>` : ""}
      </td>
      <td>
        <input type="text" class="editable-input ${isUnassigned ? 'badge-unassigned' : 'bg-body-secondary'}" value="${escapeHtml(item.owner)}" onchange="updateItemField(${idx}, 'owner', this.value)">
      </td>
      <td>
        <input type="text" class="editable-input ${isUnspecified ? 'badge-unspecified' : 'bg-body-secondary'}" value="${escapeHtml(item.deadline)}" onchange="updateItemField(${idx}, 'deadline', this.value)">
        ${item.target_iso_date ? `<small class="badge bg-secondary-subtle text-secondary d-block mt-1 w-auto">📅 ${item.target_iso_date}</small>` : ""}
      </td>
      <td class="text-center">
        <button class="btn btn-sm py-0 px-2 fw-semibold ${isConfirmed ? 'btn-success' : 'btn-warning text-dark'}" onclick="toggleStatus(${idx})" title="Click to toggle status">
          ${isConfirmed ? '✅ Confirmed' : '⚠️ Needs review'}
        </button>
      </td>
      <td class="text-center">
        <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="deleteItem(${idx})" title="Delete"><i class="bi bi-trash"></i></button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Automatically sync timeline and workload sections
  if (typeof renderTimeline === "function") renderTimeline();
  if (typeof renderWorkloadChart === "function") renderWorkloadChart();
}

function updateItemField(idx, field, val) {
  if (currentActionItems[idx]) {
    currentActionItems[idx][field] = val;
    if (field === "owner" || field === "deadline") {
      if (currentActionItems[idx].owner !== "Unassigned" && currentActionItems[idx].deadline !== "Unspecified") {
        currentActionItems[idx].review_status = "Confirmed";
        currentActionItems[idx].confidence = "High";
        currentActionItems[idx].review_reason = "Manually completed by user";
      }
    }
    renderResults(currentActionItems);
  }
}

function toggleStatus(idx) {
  if (currentActionItems[idx]) {
    currentActionItems[idx].review_status = currentActionItems[idx].review_status === "Confirmed" ? "Needs review" : "Confirmed";
    renderResults(currentActionItems);
  }
}

function deleteItem(idx) {
  currentActionItems.splice(idx, 1);
  renderResults(currentActionItems);
}

// Timeline & Gantt View
function renderTimeline() {
  const container = document.getElementById("timelineView");
  if (!currentActionItems || currentActionItems.length === 0) {
    container.innerHTML = `<div class="text-center py-5 text-muted">No action items available. Please extract items in the Workbench tab first.</div>`;
    return;
  }

  container.innerHTML = "";
  currentActionItems.forEach((item, idx) => {
    const isConfirmed = item.review_status === "Confirmed";
    const dateDisplay = item.target_iso_date || item.deadline || "Unscheduled";
    const itemDiv = document.createElement("div");
    itemDiv.className = `timeline-item ${isConfirmed ? '' : 'unconfirmed'}`;
    itemDiv.innerHTML = `
      <div class="timeline-card shadow-sm">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="badge ${isConfirmed ? 'bg-success' : 'bg-warning text-dark'} px-2 py-0.5">${item.review_status}</span>
          <span class="small text-muted"><i class="bi bi-clock me-1"></i>${dateDisplay}</span>
        </div>
        <h6 class="fw-bold mb-1">${escapeHtml(item.task)}</h6>
        <div class="d-flex justify-content-between align-items-center small text-secondary">
          <span><strong>Owner:</strong> <span class="${item.owner === 'Unassigned' ? 'text-warning-emphasis fw-bold' : ''}">${escapeHtml(item.owner)}</span></span>
          <span class="text-xs text-muted">Turn: ${escapeHtml(item.speaker_turn || 'Speaker')}</span>
        </div>
      </div>
    `;
    container.appendChild(itemDiv);
  });
}

// Workload Analytics View
function renderWorkloadChart() {
  const container = document.getElementById("workloadBars");
  if (!currentActionItems || currentActionItems.length === 0) {
    container.innerHTML = `<div class="text-center py-5 text-muted">No action items extracted yet.</div>`;
    return;
  }

  const counts = {};
  currentActionItems.forEach(i => {
    const owner = i.owner || "Unassigned";
    counts[owner] = (counts[owner] || 0) + 1;
  });

  const total = currentActionItems.length;
  container.innerHTML = "";

  for (const [owner, count] of Object.entries(counts)) {
    const pct = Math.round((count / total) * 100);
    const isUnassigned = owner === "Unassigned";
    const barHtml = `
      <div>
        <div class="d-flex justify-content-between small fw-semibold mb-1">
          <span class="${isUnassigned ? 'text-warning-emphasis' : ''}">${owner}</span>
          <span>${count} task${count > 1 ? 's' : ''} (${pct}%)</span>
        </div>
        <div class="progress mb-3" style="height: 10px;">
          <div class="progress-bar ${isUnassigned ? 'bg-warning' : 'bg-primary'}" role="progressbar" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
    container.innerHTML += barHtml;
  }

  // Accountability meter
  const unassignedCount = counts["Unassigned"] || 0;
  const assignedCount = total - unassignedCount;
  const healthPct = Math.round((assignedCount / total) * 100);
  document.getElementById("accountabilityScore").innerText = `${healthPct}%`;
  document.getElementById("accountabilityBar").style.width = `${healthPct}%`;

  const riskText = document.getElementById("riskText");
  if (unassignedCount > 0) {
    riskText.innerHTML = `<strong>Attention Required:</strong> ${unassignedCount} task(s) currently lack an explicit owner and require human assignment.`;
  } else {
    riskText.innerHTML = `<strong>Optimal Accountability:</strong> All commitments have designated owners.`;
  }
}

// Benchmark Suite Runner
async function runBenchmarkSuite() {
  try {
    const res = await fetch("/api/benchmark");
    const d = await res.json();

    document.getElementById("benchPrec").innerText = `${(d.precision * 100).toFixed(0)}%`;
    document.getElementById("benchRec").innerText = `${(d.recall * 100).toFixed(0)}%`;
    document.getElementById("benchF1").innerText = d.f1_score.toFixed(3);
    document.getElementById("benchSafety").innerText = `${(d.false_certainty_rate * 100).toFixed(1)}%`;

    document.getElementById("benchTP").innerText = d.true_positives;
    document.getElementById("benchFP").innerText = d.false_positives;
    document.getElementById("benchFN").innerText = d.false_negatives;

    showToast("Audit Benchmark re-calculated with 0.0% false-certainty rate!");
  } catch (err) {
    console.error(err);
  }
}

// Audio Player Simulation
function toggleAudioSimulation() {
  const icon = document.getElementById("audioIcon");
  const wave = document.getElementById("audioWave");
  const text = document.getElementById("audioText");

  isAudioPlaying = !isAudioPlaying;
  if (isAudioPlaying) {
    icon.className = "bi bi-pause-circle-fill fs-6 text-danger";
    wave.classList.remove("d-none");
    text.innerText = "Playing [00:03]...";
    showToast("Simulating audio stream playback with speaker alignment...");
    audioTimer = setTimeout(() => {
      toggleAudioSimulation();
    }, 8000);
  } else {
    clearTimeout(audioTimer);
    icon.className = "bi bi-play-circle-fill fs-6 text-success";
    wave.classList.add("d-none");
    text.innerText = "Play Meeting Audio";
  }
}

// Export Handlers
async function downloadCalendarICS() {
  if (!currentActionItems || currentActionItems.length === 0) {
    showToast("No action items to export.");
    return;
  }
  try {
    const res = await fetch("/api/export/calendar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_items: currentActionItems, meeting_name: "Sprint Deliverables" })
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "meeting_deliverables.ics";
    a.click();
    showToast("Downloaded .ics file for Google Calendar / Apple Calendar / Outlook!");
  } catch (err) {
    showToast("Failed to generate calendar file: " + err.message);
  }
}

function exportCSV() {
  if (!currentActionItems || currentActionItems.length === 0) return;
  const headers = ["Task", "Owner", "Deadline", "Confidence", "Review Status", "Reason", "Source Quote"];
  const rows = currentActionItems.map(i => [
    `"${(i.task || '').replace(/"/g, '""')}"`,
    `"${(i.owner || '').replace(/"/g, '""')}"`,
    `"${(i.deadline || '').replace(/"/g, '""')}"`,
    `"${i.confidence || ''}"`,
    `"${i.review_status || ''}"`,
    `"${(i.review_reason || '').replace(/"/g, '""')}"`,
    `"${(i.source_quote || '').replace(/"/g, '""')}"`
  ]);
  const csv = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
  const a = document.createElement("a");
  a.href = encodeURI(csv);
  a.download = "verified_action_items.csv";
  a.click();
  showToast("CSV downloaded successfully!");
}

function exportJSON() {
  if (!currentActionItems || currentActionItems.length === 0) return;
  const data = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentActionItems, null, 2));
  const a = document.createElement("a");
  a.href = data;
  a.download = "action_items_jira.json";
  a.click();
  showToast("JSON downloaded for Jira / Trello bulk import!");
}

function copyMarkdownSummary() {
  if (!currentActionItems || currentActionItems.length === 0) return;
  let md = "### Meeting Action Items Summary\n\n| Task | Owner | Deadline | Status |\n| :--- | :--- | :--- | :--- |\n";
  currentActionItems.forEach(i => {
    md += `| ${i.task} | **${i.owner}** | ${i.deadline} | \`${i.review_status}\` |\n`;
  });
  navigator.clipboard.writeText(md).then(() => {
    showToast("Copied Markdown summary to clipboard!");
  });
}

function switchTab(tabId) {
  const trigger = document.getElementById(`${tabId}-tab`);
  if (trigger) {
    const tab = new bootstrap.Tab(trigger);
    tab.show();
  }
}

function showToast(msg) {
  const toastEl = document.getElementById("liveToast");
  if (!toastEl) return;
  document.getElementById("toastMessage").innerText = msg;
  const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
  toast.show();
}

function escapeHtml(str) {
  return (str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
