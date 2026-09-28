// ── Per-site detection logic ────────────────────────────────────────────────
//
// Each detector returns { novelTitle, chapter, slug, sourceUrl, ... } or null.
// `chapter` is a string such as "12", "2.5" or "0.01" (never parseInt'd:
// that turned "2.5" into 2). `ambiguous: true` marks a number read from a URL
// like ".../chapter-2-5", where "2-5" might be chapter 2.5 or part 5 of
// chapter 2; the app keeps it only if the site's chapter list has 2.5.

// "chapter-12", "chapter_12", "chapter12", and "chapter-2-5" at the end of a
// path segment.
function _chapterFromPath(pathTail) {
  const m = pathTail.match(/chapter[-_]?(\d+)(?:[-_](\d+)(?=$|[/?#.]))?/i);
  if (!m) return null;
  return m[2] ? { chapter: `${m[1]}.${m[2]}`, ambiguous: true } : { chapter: m[1], ambiguous: false };
}

const DETECTORS = {

  /** novelfire.net
   *  Chapter URL:  /book/{novel-slug}/chapter-{N}
   *  Novel URL:    /book/{novel-slug}
   */
  "novelfire.net": () => {
    const m = location.pathname.match(/\/book\/([^/]+)\/(chapter[^/]*)/i);
    if (!m) return null;
    const slug = m[1];
    const ch = _chapterFromPath(m[2]);
    if (!ch) return null;

    // Try breadcrumb → h1 → og:title
    const novelTitle =
      document.querySelector(".breadcrumb a:nth-child(2)")?.textContent?.trim() ||
      document.querySelector("h1.chapter-title ~ a, .chapter-novel-title, .novel-title")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|]\s*chapter\s*\d+.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    // Best-effort source URL for the novel's info page
    const sourceUrl = `${location.origin}/book/${slug}`;
    return { novelTitle, ...ch, slug, sourceUrl };
  },

  /** novelphoenix.com — same underlying template as novelfire, but with
   *  /novel/ instead of /book/ in the URL.
   *  Chapter URL:  /novel/{novel-slug}/chapter-{N}
   *  Novel URL:    /novel/{novel-slug}
   */
  "novelphoenix.com": () => {
    const m = location.pathname.match(/\/novel\/([^/]+)\/(chapter[^/]*)/i);
    if (!m) return null;
    const slug = m[1];
    const ch = _chapterFromPath(m[2]);
    if (!ch) return null;

    // The chapter page's h1 contains a link back to the novel info page
    // whose text is the novel title, e.g. <h1><a href="/novel/{slug}">Title</a> Chapter N: ...</h1>
    const novelTitle =
      document.querySelector(`h1 a[href*='/novel/${slug}']`)?.textContent?.trim() ||
      document.querySelector(".breadcrumb a:nth-child(2)")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|]\s*chapter\s*\d+.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    const sourceUrl = `${location.origin}/novel/${slug}`;
    return { novelTitle, ...ch, slug, sourceUrl };
  },

  /** freewebnovel.com
   *  Chapter URL:  /{novel-slug}/chapter-{N}.html  or  /{novel-slug}/chapter-{N}
   *  Novel URL:    /{novel-slug}.html  or  /{novel-slug}/
   */
  "freewebnovel.com": () => {
    const m = location.pathname.match(/\/([^/]+)\/(chapter[-_][^/]*)/i);
    if (!m) return null;
    const slug = m[1];
    const ch = _chapterFromPath(m[2]);
    if (!ch) return null;

    const novelTitle =
      document.querySelector(".chapter-novel a, .breadcrumb a")?.textContent?.trim() ||
      document.querySelector("h1.title")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|]\s*chapter\s*\d+.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    const sourceUrl = `${location.origin}/${slug}.html`;
    return { novelTitle, ...ch, slug, sourceUrl };
  },

  /** wuxiaworld.com
   *  Chapter URL:  /novel/{novel-slug}/{novel-slug}-chapter-{N}
   *                /novel/{novel-slug}/chapter-{N}
   *  Novel URL:    /novel/{novel-slug}
   */
  "wuxiaworld.com": () => {
    const m = location.pathname.match(/\/novel\/([^/]+)\/((?:[^/]+-)?chapter[^/]*)/i);
    if (!m) return null;
    const slug = m[1];
    const ch = _chapterFromPath(m[2]);
    if (!ch) return null;

    const novelTitle =
      document.querySelector(".chapter-sidebar .chapter-sidebar-title a, .novel-title, h1")?.textContent?.trim() ||
      _ogTitle()?.replace(/\s*[-|].*chapter.*/i, "").trim() ||
      slug.replace(/-/g, " ");

    const sourceUrl = `${location.origin}/novel/${slug}`;
    return { novelTitle, ...ch, slug, sourceUrl };
  },

  /** flamecomics.xyz (novels and manga)
   *  Chapter URL:  /novel/{id}/{16-hex token}   or   /series/{id}/{token}
   *  Novel URL:    /novel/{id}                  or   /series/{id}
   *  The URL has no chapter number, so it comes from the page title:
   *  "{Series} - {Chapter title} - Chapter 310 - Flame Comics".
   *  Flame changes chapters without reloading the page (Previous/Next), so
   *  this runs again whenever the URL or title changes (see watcher below).
   *  __NEXT_DATA__ is NOT used: it keeps describing the first chapter
   *  loaded after an in-page navigation.
   */
  "flamecomics.xyz": () => {
    const m = location.pathname.match(/^\/(novel|series)\/(\d+)\/([0-9a-f]{8,})/i);
    if (!m) return null;
    const kind = m[1].toLowerCase();
    const id = m[2];
    const t = document.title.match(/^(.*) - Chapter (\d+(?:\.\d+)?) - Flame Comics\s*$/i);
    if (!t) return null;   // title not updated yet, or not a numbered chapter
    const novelTitle = t[1].split(" - ")[0].trim();
    return {
      novelTitle,
      chapter: t[2],
      ambiguous: false,
      slug: id,
      contentType: kind === "novel" ? "novel" : "manga",
      sourceUrl: `${location.origin}/${kind}/${id}`,
    };
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

// Report the chapter now, and again whenever the page changes chapter without
// a full reload (Flame's Previous/Next buttons, other single-page sites):
// the content script itself only runs once per page load.
let _lastReported = null;
let _lastHref = location.href;
let _timer = null;

function report() {
  const info = detect();
  if (!info) return;
  const reportKey = `${location.href}|${info.chapter}`;
  if (reportKey === _lastReported) return;
  _lastReported = reportKey;
  try {
    chrome.runtime.sendMessage({
      type: "CHAPTER_DETECTED",
      payload: {
        ...info,
        url: location.href,
        hostname: _hostname(),
        detectedAt: Date.now(),
      },
    });
  } catch (e) {
    // Extension was reloaded or updated; this old content script is orphaned.
  }
}

function scheduleReport() {
  clearTimeout(_timer);
  _timer = setTimeout(report, 400);
}

report();
new MutationObserver(scheduleReport).observe(document.head || document.documentElement, {
  subtree: true, childList: true, characterData: true,
});
window.addEventListener("popstate", scheduleReport);
setInterval(() => {
  if (location.href !== _lastHref) {
    _lastHref = location.href;
    scheduleReport();
  }
}, 1000);

// Also listen for popup asking for a re-check
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "PING_CONTENT") {
    sendResponse({ info: detect(), url: location.href });
  }
});
