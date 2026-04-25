/**
 * background.js — service worker for Library of Yore extension.
 * Manages reading state and communicates with the desktop app on localhost:7337.
 */

const API = "http://127.0.0.1:7337";
const STORAGE_KEY = "loy_state";

// ── API helpers ─────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(`${API}${path}`, { method: "GET" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function isAppRunning() {
  try {
    await apiGet("/health");
    return true;
  } catch {
    return false;
  }
}

// ── State helpers ────────────────────────────────────────────────────────────

async function getState() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  return data[STORAGE_KEY] || {};
}

async function setState(patch) {
  const current = await getState();
  const next = { ...current, ...patch };
  await chrome.storage.local.set({ [STORAGE_KEY]: next });
  return next;
}

// ── Find the library entry for a detected chapter ───────────────────────────

async function findNovel(info) {
  try {
    // First try matching by source URL
    const byUrl = await apiGet(
      `/find?url=${encodeURIComponent(info.sourceUrl)}`
    );
    if (byUrl.found) return byUrl.novel;

    // Fall back to title search
    const byTitle = await apiGet(
      `/find?title=${encodeURIComponent(info.novelTitle)}`
    );
    if (byTitle.found) return byTitle.novel;

    return null;
  } catch {
    return null;
  }
}

// ── Update badge ─────────────────────────────────────────────────────────────

async function updateBadge(chapter) {
  if (chapter) {
    chrome.action.setBadgeText({ text: String(chapter) });
    chrome.action.setBadgeBackgroundColor({ color: "#d4af37" });
  } else {
    chrome.action.setBadgeText({ text: "" });
  }
}

// ── Message handler ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    switch (msg.type) {

      // Content script detected a chapter page
      case "CHAPTER_DETECTED": {
        const info = msg.payload;
        const appOnline = await isAppRunning();
        let libraryNovel = null;

        if (appOnline) {
          libraryNovel = await findNovel(info);
        }

        const state = await setState({
          reading: info,
          libraryNovel,
          appOnline,
          lastSeen: Date.now(),
        });

        await updateBadge(info.chapter);

        // Auto-sync if enabled and novel is in library and chapter is newer
        const settings = await getSettings();
        if (
          settings.autoSync &&
          appOnline &&
          libraryNovel &&
          info.chapter > libraryNovel.current_chapter
        ) {
          try {
            await apiPost("/progress", {
              novel_id: libraryNovel.id,
              chapter: info.chapter,
            });
            // Refresh library novel data
            const updated = await findNovel(info);
            await setState({ libraryNovel: updated });
          } catch (e) {
            console.error("Auto-sync failed:", e);
          }
        }

        sendResponse({ ok: true, state });
        break;
      }

      // Popup requests current state
      case "GET_STATE": {
        const state = await getState();
        const appOnline = await isAppRunning();
        await setState({ appOnline });
        sendResponse({ ...state, appOnline });
        break;
      }

      // Popup requests manual sync
      case "SYNC_NOW": {
        const { novelId, chapter } = msg;
        try {
          const result = await apiPost("/progress", {
            novel_id: novelId,
            chapter,
          });
          // Refresh the stored library novel
          const state = await getState();
          if (state.reading) {
            const updated = await findNovel(state.reading);
            await setState({ libraryNovel: updated });
          }
          sendResponse({ ok: true, result });
        } catch (e) {
          sendResponse({ ok: false, error: e.message });
        }
        break;
      }

      // Popup requests settings
      case "GET_SETTINGS": {
        sendResponse(await getSettings());
        break;
      }

      // Popup saves settings
      case "SAVE_SETTINGS": {
        await chrome.storage.local.set({ loy_settings: msg.settings });
        sendResponse({ ok: true });
        break;
      }

      // Popup requests full novel list
      case "GET_NOVELS": {
        try {
          const novels = await apiGet("/novels");
          sendResponse({ ok: true, novels });
        } catch (e) {
          sendResponse({ ok: false, error: e.message });
        }
        break;
      }

      default:
        sendResponse({ ok: false, error: "Unknown message type" });
    }
  })();
  return true; // Keep channel open for async response
});

// ── Settings helpers ─────────────────────────────────────────────────────────

async function getSettings() {
  const data = await chrome.storage.local.get("loy_settings");
  return {
    autoSync: false,
    port: 7337,
    ...data.loy_settings,
  };
}

// ── Tab change: clear badge when leaving a novel site ────────────────────────

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    const novelHosts = ["novelfire.net", "freewebnovel.com", "wuxiaworld.com", "novelupdates.com"];
    const isNovelSite = novelHosts.some((h) => tab.url?.includes(h));
    if (!isNovelSite) {
      await updateBadge(null);
    }
  } catch {
    // Tab may not be accessible
  }
});
