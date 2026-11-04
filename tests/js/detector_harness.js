// Runs the MangaFire detector from the extension's content.js against scripted pages.
// Input (stdin): [{path, title, og, headings, current, advance}], one step per page state, in order.
// Output (stdout): one JSON result per step (the detector's return value, plus the popup hint).
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..", "..", "Library of Yore Browser Extension", "content.js");
const src = fs.readFileSync(root, "utf8");
const head = src.slice(0, src.indexOf("// ── Main"));

const clock = { now: 1_000_000 };
const state = { path: "/", title: "", og: "", headings: [], current: [] };
const el = (t) => ({ textContent: t });

const location = {
  get pathname() { return state.path; },
  get href() { return "https://mangafire.to" + state.path; },
  origin: "https://mangafire.to",
  hostname: "mangafire.to",
};
const document = {
  get title() { return state.title; },
  querySelector: (sel) => (sel.includes("og:title") && state.og ? { content: state.og } : null),
  querySelectorAll: (sel) => (sel.includes("h1") ? state.headings : state.current).map(el),
};
const FakeDate = { now: () => clock.now };

const api = new Function(
  "location", "document", "Date",
  head + "; return { detect: DETECTORS['mangafire.to'], debug: () => _debug };"
)(location, document, FakeDate);

const steps = JSON.parse(fs.readFileSync(0, "utf8"));
const out = steps.map((s) => {
  Object.assign(state, { path: s.path, title: s.title || "", og: s.og || "", headings: s.headings || [], current: s.current || [] });
  clock.now += s.advance || 0;
  return { info: api.detect(), debug: api.debug() };
});
process.stdout.write(JSON.stringify(out));
