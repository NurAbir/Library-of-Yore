"""utils/chapters.py: parsing, range storage and progress."""
from utils import chapters as C


def test_parse_chapter_canonical_strings():
    assert C.parse_chapter("621.00") == "621"
    assert C.parse_chapter("16.50") == "16.5"
    assert C.parse_chapter("0.01") == "0.01"
    assert C.parse_chapter("4.20") == "4.2"
    assert C.parse_chapter(7) == "7"
    assert C.parse_chapter(0) == "0"
    assert C.parse_chapter(2.5) == "2.5"
    assert C.parse_chapter("1,234") == "1234"
    for bad in (None, "", "abc", -1, float("nan"), True, "1e9"):
        assert C.parse_chapter(bad) is None, bad


def test_is_newer_handles_not_started_and_zero():
    assert C.is_newer("0", None)          # chapter 0 from a fresh entry now counts
    assert C.is_newer("2.5", "2")
    assert not C.is_newer("2.5", "3")     # never goes backwards
    assert not C.is_newer("3", "3")
    assert not C.is_newer(None, "3")


def test_ranges_round_trip_and_size():
    flame_novel_13 = ["0.01"] + [str(n) for n in range(1, 756)]
    enc = C.encode_ranges(flame_novel_13)
    assert enc == "0.01,1-755"
    assert C.decode_ranges(enc) == sorted(flame_novel_13, key=C.key)
    orv = [str(n) for n in range(1, 622) if n not in (221, 222, 223, 224)]
    assert C.encode_ranges(orv) == "1-220,225-621"
    mixed = ["1", "2", "4.2", "3", "5.5", "5", "16.5", "6"]
    assert C.encode_ranges(mixed) == "1-3,4.2,5,5.5,6,16.5"
    assert C.decode_ranges("1-3,4.2,5,5.5,6,16.5") == ["1", "2", "3", "4.2", "5", "5.5", "6", "16.5"]
    big = [str(n) for n in range(0, 3000)]
    assert len(C.encode_ranges(big)) < 10
    assert C.decode_ranges("garbage,-,5-3,1-99999999,7") == ["7"]


def test_normalize_list_flags_duplicates():
    chs, trusted = C.normalize_list(["2.10", "2.1", "3"])
    assert chs == ["2.1", "3"] and trusted is False
    chs, trusted = C.normalize_list(["621.00", "1.00", "2.00"])
    assert chs == ["1", "2", "621"] and trusted is True


def test_list_mode_next_behind_percent():
    lst = C.encode_ranges(["0", "1", "2", "2.5", "3"])
    p = C.compute_progress(None, "3", lst)
    assert p.next_chapter == "0" and p.behind == 5 and p.percent == 0.0 and not p.up_to_date
    p = C.compute_progress("2", "3", lst)
    assert p.next_chapter == "2.5" and p.behind == 2
    p = C.compute_progress("2.5", "3", lst)
    assert p.next_chapter == "3" and p.behind == 1
    p = C.compute_progress("3", "3", lst)
    assert p.behind == 0 and p.up_to_date and p.percent == 100.0


def test_list_mode_gaps_and_count_vs_latest():
    # ORV novel: 617 entries, numbered 1..621 with 221-224 missing
    lst = "1-220,225-621"
    p = C.compute_progress("220", "621", lst)
    assert p.next_chapter == "225"
    assert p.total == 617
    p = C.compute_progress("621", "621", lst)
    assert p.up_to_date and p.behind == 0      # the old 755-vs-756 problem


def test_list_mode_partial_list_and_stale_list():
    # Manga whose list only covers chapters 94-160
    lst = "94-160"
    p = C.compute_progress("50", "160", lst)
    assert p.next_chapter == "94" and p.behind == 67
    # Site has published 161-163 but the stored list isn't refreshed yet
    p = C.compute_progress("160", "163", lst)
    assert p.next_chapter == "161" and p.behind == 3 and not p.up_to_date
    p = C.compute_progress("162", "163", lst)
    assert p.next_chapter == "163" and p.behind == 1


def test_locked_counts_only_ahead():
    p = C.compute_progress("600", "621", "1-621", "130-135,527-621")
    assert p.locked_behind == 21
    p = C.compute_progress(None, "621", "1-621", "130-135")
    assert p.locked_behind == 6


def test_simple_mode():
    p = C.compute_progress(None, "100")
    assert p.next_chapter == "1" and p.behind == 100 and p.percent == 0.0
    p = C.compute_progress("45.5", "100")
    assert p.next_chapter == "46" and p.behind == 55 and p.percent == 45.5
    p = C.compute_progress("100", "100")
    assert p.up_to_date and p.percent == 100.0 and p.next_chapter == "101"
    p = C.compute_progress("10", None)
    assert p.behind is None and not p.up_to_date and p.next_chapter == "11"


def test_resolve_reported_ambiguous_url_numbers():
    lst = "1,2,2.5,3"
    assert C.resolve_reported("2.5", True, lst) == "2.5"     # exact match in list wins
    assert C.resolve_reported("2.5", True, "1-3") == "2"      # otherwise snap to whole
    assert C.resolve_reported("2.5", True, "") == "2"
    assert C.resolve_reported("2.5", False, "") == "2.5"      # trusted source kept
