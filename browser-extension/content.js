/**
 * content.js — injected into all supported novel sites.
 * Detects the current novel title and chapter number, then
 * notifies the background service worker.
 */

// ── Per-site detection logic ────────────────────────────────────────────────

const DETECTORS = {

  /** novelfire.net
   *  Chapter URL:  /book/{novel-slug}/chapter-{N}
   *  Novel URL:    /book/{novel-slug}
   */
  "novelfire.net": () => {
    const m = location.pathname.match(/\/book\/([^/]+)\/chapter-?(\d+)/i);
    if (!m) return null;
    const slug = m[1];
    const chapter = parseInt(m[2], 10);

    // Try breadcrumb → h1 → og:title
    const novelTitle =
      document.querySelector(".breadcrumb a:nth-child(2)")?.textContent?.trim() ||
      document.querySelector("h1.chapter-title ~ a, .chapter-novel-title, .novel-title")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|]\s*chapter\s*\d+.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    // Best-effort source URL for the novel's info page
    const sourceUrl = `${location.origin}/book/${slug}`;
    return { novelTitle, chapter, slug, sourceUrl };
  },

  /** freewebnovel.com
   *  Chapter URL:  /{novel-slug}/chapter-{N}.html  or  /{novel-slug}/chapter-{N}
   *  Novel URL:    /{novel-slug}.html  or  /{novel-slug}/
   */
  "freewebnovel.com": () => {
    const m = location.pathname.match(/\/([^/]+)\/chapter[-_](\d+)/i);
    if (!m) return null;
    const slug = m[1];
    const chapter = parseInt(m[2], 10);

    const novelTitle =
      document.querySelector(".chapter-novel a, .breadcrumb a")?.textContent?.trim() ||
      document.querySelector("h1.title")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|]\s*chapter\s*\d+.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    const sourceUrl = `${location.origin}/${slug}.html`;
    return { novelTitle, chapter, slug, sourceUrl };
  },

  /** wuxiaworld.com
   *  Chapter URL:  /novel/{novel-slug}/{novel-slug}-chapter-{N}
   *                /novel/{novel-slug}/chapter-{N}
   *  Novel URL:    /novel/{novel-slug}
   */
  "wuxiaworld.com": () => {
    const m = location.pathname.match(/\/novel\/([^/]+)\/(?:[^/]+-)?chapter[-_]?(\d+)/i);
    if (!m) return null;
    const slug = m[1];
    const chapter = parseInt(m[2], 10);

    const novelTitle =
      document.querySelector(".chapter-sidebar .chapter-sidebar-title a, .novel-title, h1")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|].*chapter.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    const sourceUrl = `${location.origin}/novel/${slug}`;
    return { novelTitle, chapter, slug, sourceUrl };
  },
};

// novelupdates is a tracker site, not a reading site — no chapter detection needed
// but we still want the content script loaded so the popup works on it.

// ── Helpers ─────────────────────────────────────────────────────────────────

function _ogTitle() {
  return document.querySelector("meta[property='og:title']")?.content || "";
}

function _hostname() {
  return location.hostname.replace(/^www\./, "");
}

// ── Main ─────────────────────────────────────────────────────────────────────

function detect() {
  const detector = DETECTORS[_hostname()];
  if (!detector) return null;
  try {
    return detector();
  } catch (e) {
    return null;
  }
}

// Run detection and notify background
const info = detect();

if (info) {
  chrome.runtime.sendMessage({
    type: "CHAPTER_DETECTED",
    payload: {
      ...info,
      url: location.href,
      hostname: _hostname(),
      detectedAt: Date.now(),
    },
  });
}

// Also listen for popup asking for a re-check
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "PING_CONTENT") {
    sendResponse({ info: detect(), url: location.href });
  }
});
