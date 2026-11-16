/**
 * popup.js — drives the Library of Yore extension popup UI.
 */

// DOM references

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

// Helpers

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

// Why a supported site's page wasn't recognised

async function showIdleDebug() {
  const el = $("idle-debug");
  el.classList.add("hidden");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url) return;
    const u = new URL(tab.url);
    const sites = [...document.querySelectorAll(".site-badge")].map((b) => b.textContent.trim());
    if (!sites.some((s) => u.hostname === s || u.hostname.endsWith("." + s))) return;
    let hint = "";
    try {
      const reply = await chrome.tabs.sendMessage(tab.id, { type: "PING_CONTENT" });
      if (reply && reply.debug) hint = ` ${reply.debug}`;
    } catch (_) { /* no content script in this tab: the extension needs a reload */ }
    el.textContent =
      `This page wasn't recognised as a chapter: ${u.pathname}.${hint} ` +
      "If it is a chapter, reload the extension at chrome://extensions, then refresh the page.";
    el.classList.remove("hidden");
  } catch (_) { /* no access to the tab's URL: say nothing */ }
}

// Render

function render(state) {
  if (!state.appOnline) {
    setDot("offline");
    showView("offline");
    return;
  }

  setDot("online");

  if (!state.reading) {
    showView("idle");
    showIdleDebug();
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
    const storedCh  = novel.current_chapter;              // string, or null = not started
    const browserCh = String(state.reading.chapter);
    libChapter.textContent  = storedCh === null || storedCh === undefined ? "Not started" : `Ch ${storedCh}`;
    libProgress.textContent = `${novel.percent_complete}%`;

    const byTitle = state.libraryMatch === "title";
    const newer = storedCh === null || storedCh === undefined || parseFloat(browserCh) > parseFloat(storedCh);
    const same  = !newer && parseFloat(browserCh) === parseFloat(storedCh);

    if (newer) {
      syncState.textContent  = (storedCh === null || storedCh === undefined
          ? "Not started in your library"
          : `Ahead of your library (Ch ${storedCh})`)
        + (byTitle ? " - matched by title only: check it's the right entry" : "");
      syncState.className    = "sync-state";
      btnSync.disabled       = false;
      btnSync.textContent    = `Sync to Ch ${browserCh}`;
    } else if (same) {
      syncState.textContent  = "Up to date";
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

// Init

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

// Sync button

btnSync.addEventListener("click", async () => {
  const state = await send({ type: "GET_STATE" });
  if (!state?.reading || !state?.libraryNovel) return;

  btnSync.disabled    = true;
  btnSync.textContent = "Syncing…";
  syncState.textContent = "";

  const result = await send({
    type:    "SYNC_NOW",
    novelId:   state.libraryNovel.id,
    chapter:   String(state.reading.chapter),
    ambiguous: !!state.reading.ambiguous,
  });

  if (result?.ok) {
    syncState.className   = "sync-state sync-state--success";
    syncState.textContent = `Synced to Ch ${state.reading.chapter}`;
    btnSync.textContent   = "Already synced";
    btnSync.disabled      = true;
    // Refresh lib chapter display
    libChapter.textContent = `Ch ${state.reading.chapter}`;
  } else {
    syncState.className   = "sync-state sync-state--error";
    syncState.textContent = `${result?.error || "Sync failed"}`;
    btnSync.disabled      = false;
    btnSync.textContent   = "Retry Sync";
  }
});

// Settings panel

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

// Boot

document.addEventListener("DOMContentLoaded", init);
