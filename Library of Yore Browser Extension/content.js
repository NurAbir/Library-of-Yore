// Per-site detection logic
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

    // Try breadcrumb -> h1 -> og:title
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
   *  Chapter URL:  /novel/{novel-slug}/chapter-{N}  (older: /{novel-slug}/chapter-{N}.html)
   *  Novel URL:    /novel/{novel-slug}              (older: /{novel-slug}.html)
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

    // Current site layout: /novel/{slug}/chapter-{N}; older: /{slug}/chapter-{N}.html
    const sourceUrl = /^\/novel\//i.test(location.pathname)
      ? `${location.origin}/novel/${slug}`
      : `${location.origin}/${slug}.html`;
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
    // Some older Wuxiaworld novels number chapters as book.chapter: the URL
    // "cd-book-21-chapter-44" is chapter 21.044 on the site, so record it
    // that way to match the chapter numbers the app gets from Wuxiaworld.
    const book = m[2].match(/book-(\d+)-chapter-(\d+)/i);
    const ch = book
      ? { chapter: `${parseInt(book[1], 10)}.${book[2].padStart(3, "0")}`, ambiguous: false }
      : _chapterFromPath(m[2]);
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

  /** mangafire.to (manga, manhwa, manhua, one-shots)
   *  A series has a stable short id plus a slug that can change:
   *    current  /title/{id}-{slug}          older  /manga/{slug}.{id}, /read/{slug}.{id}/{lang}/chapter-{N}
   *  The older forms redirect to the current one. Older reader URLs end in "chapter-{N}".
   *  The current reader URL is /title/{id}-{slug}/chapter/{internal chapter id}: that
   *  internal id is NOT the chapter number, which is read from the page (tab title,
   *  headings, the selected chapter). The language, if any, is ignored: chapters are
   *  matched against the series. The app matches the saved series by its id. Volumes
   *  aren't tracked.
   */
  "mangafire.to": () => {
    const segs = location.pathname.split("/").filter(Boolean);
    if (segs.length < 3 || !["title", "manga", "read"].includes(segs[0].toLowerCase())) return null;

    const series = segs[1].toLowerCase();
    const older = /^(.+)\.([a-z0-9]{2,8})$/.exec(series);                 // slug.id
    const current = !older && /^([a-z0-9]{2,8})-(.+)$/.exec(series);      // id-slug
    const bare = !older && !current && /^(?=[a-z]*\d)[a-z0-9]{2,8}$/.test(series);   // id alone (has a digit)
    if (!older && !current && !bare) return null;
    const slug = older ? older[1] : current ? current[2] : "";

    let chapter = null;
    let ambiguous = false;
    const rest = segs.slice(2);
    for (const seg of rest) {
      // older reader URLs: chapter-7, chapter-7.2, chapter-7-2, chapter7, ch-7
      const c = /^(?:chapter|chap|ch)[-_.]?(\d+)(?:([.-])(\d+))?$/i.exec(seg);
      if (c) {
        // "7.2" is plainly 7.2; "7-2" could be 7.2 or part 2 of chapter 7
        chapter = c[3] ? `${c[1]}.${c[3]}` : c[1];
        ambiguous = c[2] === "-";
        break;
      }
    }

    // Current reader URLs: /title/{id}-{slug}/chapter/{internal chapter id}. That id is NOT the
    // chapter number (e.g. 8205410), so the number has to come from the page itself.
    const at = rest.findIndex((s) => s.toLowerCase() === "chapter");
    if (chapter === null && at >= 0 && /^\d+$/.test(rest[at + 1] || "")) {
      const href = location.href;
      if (_mfNav.href !== href) _mfNav = { href, prev: _mfLast.chapter, since: Date.now() };
      const found = _chapterCandidates();
      // Just after in-page navigation the page can still show the previous chapter: skip
      // that value for a few seconds rather than report the wrong chapter.
      const fresh = Date.now() - _mfNav.since < 4000 && _mfNav.prev !== null
        ? found.find((n) => n !== _mfNav.prev)
        : found[0];
      if (fresh === undefined) {
        _debug = `chapter page (id ${rest[at + 1]}) but no chapter number: ${_pageHints()}`;
        return null;
      }
      chapter = fresh;
    }
    if (chapter === null) return null;     // the series page itself, a volume, ...
    _debug = "";
    _mfLast = { chapter };

    // The un-rendered page carries the site's generic title; never use that as the novel's
    const usable = (t) => (t && !/mangafire|read manga|manga online|free online/i.test(t) ? t : "");
    // "Title - Chapter 12", "Title Manga, Chapter 12", "Title Ch. 7": strip the chapter part
    const fromTitle = document.title
      .replace(/\s*[-–|,]?\s*(?:chapter|chap|ch)\b\.?\s*#?\s*\d+(?:\.\d+)?\b.*$/i, "")
      .replace(/\s+Manga\s*$/i, "")
      .trim();
    const novelTitle =
      usable(fromTitle) ||
      usable(_ogTitle()?.replace(/^Read\s+/i, "").replace(/\s+Manga\b.*$/i, "").trim()) ||
      (slug || series).replace(/-/g, " ");

    return {
      novelTitle,
      chapter,
      ambiguous,
      slug: series,
      contentType: "manga",
      sourceUrl: `${location.origin}/${older ? "manga" : "title"}/${series}`,
    };
  },
};

// Helpers

function _ogTitle() {
  return document.querySelector("meta[property='og:title']")?.content || "";
}

// Chapter number read from the page (for sites whose chapter URLs carry only an internal id)

// "Chapter 123", "Chap 12.5", "Ch. 7": the keyword must start a word, so "Search 12" never matches
const _CHAPTER_LABEL = /\b(?:chapter|chap|ch)\b\.?\s*#?\s*(\d+(?:\.\d+)?)/i;

function _texts(selector) {
  return [...document.querySelectorAll(selector)].map((e) => (e.textContent || "").replace(/\s+/g, " ").trim());
}

/** Chapter numbers the page states, most trustworthy source first, without repeats:
 *  the tab title, og:title, headings, then whatever is marked as the current/selected item. */
function _chapterCandidates() {
  const sources = [
    [document.title],
    [_ogTitle()],
    _texts("h1, h2, h3"),
    _texts('[aria-current], [aria-selected="true"], option:checked, .active, .current, .selected'),
  ];
  const found = [];
  for (const texts of sources) {
    for (const t of texts) {
      const m = _CHAPTER_LABEL.exec(t || "");
      if (m && !found.includes(m[1])) found.push(m[1]);
    }
  }
  return found;
}

/** What the page offered, for the popup to show when no chapter number could be read. */
function _pageHints() {
  const cut = (s) => (s.length > 70 ? s.slice(0, 70) + "…" : s);
  const list = (sel) => _texts(sel).filter(Boolean).slice(0, 3).map(cut).join(" | ");
  return `title="${cut(document.title || "")}"; og="${cut(_ogTitle())}"; ` +
         `headings="${list("h1, h2, h3")}"; current="${list('[aria-current], [aria-selected="true"], option:checked, .active, .current, .selected')}"`;
}

let _debug = "";           // set by a detector that found a chapter page but no number
let _mfLast = { chapter: null };
let _mfNav = { href: "", prev: null, since: 0 };

function _hostname() {
  return location.hostname.replace(/^www\./, "");
}

// Main

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

// MangaFire's chapter number may only change in the page body (not the tab title), which the
// observer above doesn't watch, so look again periodically; report() ignores repeats.
if (_hostname() === "mangafire.to") setInterval(scheduleReport, 1500);

// Also listen for popup asking for a re-check
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "PING_CONTENT") {
    sendResponse({ info: detect(), url: location.href, debug: _debug });
  }
});
