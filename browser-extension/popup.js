/**
 * popup.js — drives the Library of Yore extension popup UI.
 */

// ── DOM references ───────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);

const dot            = $("connection-dot");
const viewOffline    = $("view-offline");
const viewIdle       = $("view-idle");
const viewReading    = $("view-reading");

const readingTitle   = $("reading-title");
const readingChapter = $("reading-chapter");
const readingSite    = $("reading-site");

const libraryCard    = $("library-card");
const libFound       = $("lib-found");
const libNotFound    = $("lib-not-found");
const libTitle       = $("lib-title");
const libChapter     = $("lib-chapter");
const libProgress    = $("lib-progress");
const syncState      = $("sync-state");

const btnSync        = $("btn-sync");
const btnSettings    = $("btn-settings");
const btnSettingsClose = $("btn-settings-close");
const btnSaveSettings  = $("btn-save-settings");
const settingsPanel  = $("settings-panel");
const settingAutoSync = $("setting-autosync");

// ── Helpers ──────────────────────────────────────────────────────────────────

function showView(name) {
  viewOffline.classList.add("hidden");
  viewIdle.classList.add("hidden");
  viewReading.classList.add("hidden");
  if (name === "offline")  viewOffline.classList.remove("hidden");
  if (name === "idle")     viewIdle.classList.remove("hidden");
  if (name === "reading")  viewReading.classList.remove("hidden");
}

function send(msg) {
  return new Promise((resolve) =>
    chrome.runtime.sendMessage(msg, resolve)
  );
}

function setDot(state) {
  dot.className = "dot";
  if (state === "online")  dot.className += " dot--online";
  if (state === "offline") dot.className += " dot--offline";
  if (state === "connecting") dot.className += " dot--connecting";
  dot.title = state === "online"
    ? "Library of Yore is running"
    : state === "offline"
    ? "Library of Yore is not running"
    : "Connecting…";
}

function capitalize(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

// ── Render ───────────────────────────────────────────────────────────────────

function render(state) {
  if (!state.appOnline) {
    setDot("offline");
    showView("offline");
    return;
  }

  setDot("online");

  if (!state.reading) {
    showView("idle");
    return;
  }

  showView("reading");

  // Reading card
  readingTitle.textContent   = state.reading.novelTitle || "Unknown Novel";
  readingChapter.textContent = `Ch ${state.reading.chapter}`;
  readingSite.textContent    = state.reading.hostname || "";

  // Library card
  const novel = state.libraryNovel;

  if (novel) {
    libFound.classList.remove("hidden");
    libNotFound.classList.add("hidden");
    libraryCard.style.borderLeftColor = "#d4af37";

    libTitle.textContent    = novel.title;
    libChapter.textContent  = `Ch ${novel.current_chapter}`;
    libProgress.textContent = `${novel.percent_complete}%`;

    const browserCh = state.reading.chapter;
    const storedCh  = novel.current_chapter;

    if (browserCh > storedCh) {
      syncState.textContent  = `⬆ ${browserCh - storedCh} chapter${browserCh - storedCh > 1 ? "s" : ""} ahead`;
      syncState.className    = "sync-state";
      btnSync.disabled       = false;
      btnSync.textContent    = `Sync to Ch ${browserCh}`;
    } else if (browserCh === storedCh) {
      syncState.textContent  = "✓ Up to date";
      syncState.className    = "sync-state sync-state--already";
      btnSync.disabled       = true;
      btnSync.textContent    = "Already synced";
    } else {
      syncState.textContent  = `Library is ahead (Ch ${storedCh})`;
      syncState.className    = "sync-state sync-state--already";
      btnSync.disabled       = true;
      btnSync.textContent    = "Library is ahead";
    }
  } else {
    libFound.classList.add("hidden");
    libNotFound.classList.remove("hidden");
    libraryCard.style.borderLeftColor = "#333";
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  setDot("connecting");

  const state = await send({ type: "GET_STATE" });
  render(state || {});

  // Load settings
  const settings = await send({ type: "GET_SETTINGS" });
  if (settings) {
    settingAutoSync.checked = settings.autoSync || false;
  }
}

// ── Sync button ───────────────────────────────────────────────────────────────

btnSync.addEventListener("click", async () => {
  const state = await send({ type: "GET_STATE" });
  if (!state?.reading || !state?.libraryNovel) return;

  btnSync.disabled    = true;
  btnSync.textContent = "Syncing…";
  syncState.textContent = "";

  const result = await send({
    type:    "SYNC_NOW",
    novelId: state.libraryNovel.id,
    chapter: state.reading.chapter,
  });

  if (result?.ok) {
    syncState.className   = "sync-state sync-state--success";
    syncState.textContent = `✓ Synced to Ch ${state.reading.chapter}`;
    btnSync.textContent   = "Already synced";
    // Refresh lib chapter display
    libChapter.textContent = `Ch ${state.reading.chapter}`;
  } else {
    syncState.className   = "sync-state sync-state--error";
    syncState.textContent = `✗ ${result?.error || "Sync failed"}`;
    btnSync.disabled      = false;
    btnSync.textContent   = "Retry Sync";
  }
});

// ── Settings panel ────────────────────────────────────────────────────────────

btnSettings.addEventListener("click", () => {
  settingsPanel.classList.toggle("hidden");
});

btnSettingsClose.addEventListener("click", () => {
  settingsPanel.classList.add("hidden");
});

btnSaveSettings.addEventListener("click", async () => {
  await send({
    type:     "SAVE_SETTINGS",
    settings: { autoSync: settingAutoSync.checked },
  });
  settingsPanel.classList.add("hidden");

  // Refresh display (auto-sync may have changed behaviour)
  const state = await send({ type: "GET_STATE" });
  render(state || {});
});

// ── Boot ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", init);
