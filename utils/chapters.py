"""Chapter numbers, chapter lists and reading-progress logic (since v2.1.0).

Every chapter number in Library of Yore is a short canonical string such as
"12", "2.5" or "0.01", compared exactly with Decimal. They are never floats:
floats can't tell 2.1 from 2.10 apart reliably, and a float sent through a Qt
signal declared as int silently arrives as a garbage number.

A site's full chapter list, when a scraper can read one, is stored compactly
as ranges: "0.01,1-755" instead of 756 separate numbers. Progress is then
based on position in that list (which handles chapter 0, decimals, gaps and
lists that start part-way) instead of dividing chapter numbers. Novels
without a list fall back to "simple mode": whole chapters 1..latest.

Pure Python, no Qt, so it is shared by the app, the API server and tests.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Iterable, List, Optional, Tuple

# Guards against absurd values from a bad page or a typo.
MAX_CHAPTER = Decimal(1_000_000)
MAX_RANGE_SPAN = 200_000


# ── Single chapter numbers ────────────────────────────────────────────────────

def _to_decimal(value) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                return None
            d = Decimal(repr(value))
        else:
            text = str(value).strip().replace(",", "")
            if not text:
                return None
            d = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite() or d < 0 or d > MAX_CHAPTER:
        return None
    return d


def _fmt(d: Decimal) -> str:
    text = format(d.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_chapter(value) -> Optional[str]:
    """Canonical chapter string, or None if the value isn't a chapter number.
    "621.00" -> "621", 2.5 -> "2.5", "0.01" -> "0.01", 7 -> "7", "" -> None."""
    d = _to_decimal(value)
    return None if d is None else _fmt(d)


def key(chapter: str) -> Decimal:
    """Sort/compare key for a canonical chapter string."""
    return Decimal(chapter)


def floor_chapter(chapter: str) -> str:
    return _fmt(key(chapter).to_integral_value(rounding=ROUND_FLOOR))


def is_newer(new: Optional[str], current: Optional[str]) -> bool:
    """True if `new` is further along than `current`. Any chapter (including
    0) is newer than None, which means "not started"."""
    if new is None:
        return False
    if current is None:
        return True
    return key(new) > key(current)


def display(chapter: Optional[str], empty: str = "–") -> str:
    return chapter if chapter is not None else empty


# ── Chapter lists as compact ranges ───────────────────────────────────────────

def normalize_list(values: Iterable) -> Tuple[List[str], bool]:
    """Parse, de-duplicate and sort chapter numbers ascending.

    Returns (chapters, trusted). trusted is False when two entries turn out to
    be the same number (e.g. "2.1" and "2.10", or a volume restarting at 1),
    because position-based progress can't be relied on for such a list."""
    parsed = [c for c in (parse_chapter(v) for v in values) if c is not None]
    unique = sorted(set(parsed), key=key)
    return unique, len(unique) == len(parsed)


def encode_ranges(chapters: Iterable[str]) -> str:
    """["0.01","1","2","3","5"] -> "0.01,1-3,5". Input needn't be sorted."""
    items = sorted({c for c in (parse_chapter(v) for v in chapters) if c is not None}, key=key)
    out: List[str] = []
    i = 0
    while i < len(items):
        start = items[i]
        if "." not in start:
            j = i
            while (
                j + 1 < len(items)
                and "." not in items[j + 1]
                and int(items[j + 1]) == int(items[j]) + 1
            ):
                j += 1
            out.append(start if j == i else f"{start}-{items[j]}")
            i = j + 1
        else:
            out.append(start)
            i += 1
    return ",".join(out)


def decode_ranges(text: Optional[str]) -> List[str]:
    """Inverse of encode_ranges. Malformed pieces are skipped."""
    if not text:
        return []
    result = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            if lo.isdigit() and hi.isdigit() and int(lo) <= int(hi) and int(hi) - int(lo) <= MAX_RANGE_SPAN:
                result.update(str(n) for n in range(int(lo), int(hi) + 1))
            continue
        chapter = parse_chapter(part)
        if chapter is not None:
            result.add(chapter)
    return sorted(result, key=key)


# ── Reading progress ──────────────────────────────────────────────────────────

@dataclass
class Progress:
    next_chapter: str             # what "+1" moves to
    behind: Optional[int]         # chapters left to read (None = unknown)
    total: Optional[int]          # chapters the site has, as far as known
    percent: float                # 0-100
    up_to_date: bool
    locked_behind: int            # of the chapters left, how many are locked/paid
    mode: str                     # "list" or "simple"


def compute_progress(current: Optional[str], latest: Optional[str],
                     chapter_list: Optional[str] = "", locked_list: Optional[str] = "") -> Progress:
    cur = key(current) if current is not None else None
    lat = key(latest) if latest is not None else None
    chapters = decode_ranges(chapter_list)
    locked = [key(c) for c in decode_ranges(locked_list)]
    locked_behind = sum(1 for k in locked if cur is None or k > cur)

    def after_floor() -> str:
        return "1" if cur is None else _fmt(cur.to_integral_value(rounding=ROUND_FLOOR) + 1)

    if chapters:
        keys = [key(c) for c in chapters]
        last = keys[-1]
        if lat is None or lat < last:
            lat = last
        ahead = [c for c, k in zip(chapters, keys) if cur is None or k > cur]
        read = len(chapters) - len(ahead)
        if cur is not None and cur > last:
            read += int(cur.to_integral_value(rounding=ROUND_FLOOR)) - int(last.to_integral_value(rounding=ROUND_FLOOR))

        # The site has published past the end of the stored list (list is
        # stale until the next refresh): count those as whole chapters.
        extra = 0
        if lat > last:
            base = max(last, cur) if cur is not None else last
            extra = max(0, int(lat.to_integral_value(rounding=ROUND_FLOOR))
                        - int(base.to_integral_value(rounding=ROUND_FLOOR)))
        behind = len(ahead) + extra
        total = len(chapters) + max(0, int(lat.to_integral_value(rounding=ROUND_FLOOR))
                                    - int(last.to_integral_value(rounding=ROUND_FLOOR)))
        percent = round(100.0 * min(read, total) / total, 1) if total else 0.0
        if behind == 0 and cur is not None:
            percent = 100.0
        next_chapter = ahead[0] if ahead else after_floor()
        return Progress(next_chapter, behind, total, percent, behind == 0 and cur is not None,
                        locked_behind, "list")

    # Simple mode: whole chapters 1..latest.
    next_chapter = after_floor()
    if lat is None:
        return Progress(next_chapter, None, None, 0.0, False, locked_behind, "simple")
    lat_floor = int(lat.to_integral_value(rounding=ROUND_FLOOR))
    if cur is None:
        behind = max(lat_floor, 1)
        percent = 0.0
    else:
        behind = max(0, lat_floor - int(cur.to_integral_value(rounding=ROUND_FLOOR)))
        percent = 100.0 if lat == 0 else round(min(100.0, float(cur / lat * 100)), 1)
    return Progress(next_chapter, behind, lat_floor or None, percent,
                    cur is not None and behind == 0, locked_behind, "simple")


def resolve_reported(chapter: Optional[str], ambiguous: bool, chapter_list: Optional[str]) -> Optional[str]:
    """A chapter number read from a URL like ".../chapter-2-5" is ambiguous
    (2.5? part 5 of chapter 2?). Keep it only if the stored list has exactly
    that chapter; otherwise fall back to the whole chapter (2)."""
    if chapter is None or not ambiguous:
        return chapter
    if chapter in decode_ranges(chapter_list):
        return chapter
    return floor_chapter(chapter)
