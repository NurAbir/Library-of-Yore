"""Browser-extension API: URL/title matching and origin checks."""
from database.models import Novel
import api_server as api


def _lib():
    return [
        Novel(_id="solo", title="Solo Leveling", source_url="https://flamecomics.xyz/series/1"),
        Novel(_id="orv-m", title="Omniscient Reader's Viewpoint", source_url="https://flamecomics.xyz/series/2"),
        Novel(_id="orv-n", title="Omniscient Reader's Viewpoint", source_url="https://flamecomics.xyz/novel/8"),
        Novel(_id="ss", title="Shadow Slave", source_url="https://novelfire.net/book/shadow-slave"),
        Novel(_id="ss2", title="Shadow Slave Side Stories", source_url="https://novelfire.net/book/shadow-slave-side"),
        Novel(_id="lotm", title="Lord of the Mysteries", source_url="https://freewebnovel.com/novel/lord-of-the-mysteries"),
        Novel(_id="ri", title="Renegade Immortal", source_url="https://www.wuxiaworld.com/novel/renegade-immortal"),
        Novel(_id="manual", title="Some Manual Entry", source_url=""),
    ]


def _find(url):
    n = api._find_by_url(_lib(), url)
    return n._id if n else None


def test_numeric_ids_match_whole_segments_only():
    # Before 2.0.2 all three of these matched Solo Leveling or the ORV manhwa.
    assert _find("https://flamecomics.xyz/series/21/abcdef0123456789") is None
    assert _find("https://flamecomics.xyz/series/112/abcdef0123456789") is None
    assert _find("https://flamecomics.xyz/novel/8/f48067c3fe28e0a0") == "orv-n"
    assert _find("https://flamecomics.xyz/series/2/364db6fd6bef182e") == "orv-m"
    assert _find("https://flamecomics.xyz/series/1/364db6fd6bef182e") == "solo"


def test_existing_sites_still_match():
    assert _find("https://novelfire.net/book/shadow-slave/chapter-2100") == "ss"
    assert _find("https://www.novelfire.net/book/shadow-slave/chapter-5") == "ss"
    assert _find("https://novelfire.net/book/shadow-slave-side/chapter-5") == "ss2"
    assert _find("https://www.wuxiaworld.com/novel/renegade-immortal/ri-chapter-12") == "ri"
    # FreeWebNovel chapter URLs drop the /novel/ prefix: distinctive-slug fallback
    assert _find("https://freewebnovel.com/lord-of-the-mysteries/chapter-12.html") == "lotm"


def test_domain_must_match():
    assert _find("https://novelphoenix.com/novel/shadow-slave/chapter-3") is None


def test_title_fallback_is_title_only_and_same_site():
    lib = _lib()
    lib.append(Novel(_id="notes", title="Unrelated", notes="better than Shadow Slave",
                     source_url="https://novelfire.net/book/unrelated"))
    # exact title, same site
    assert api._find_by_title(lib, "Shadow Slave", "novelfire.net")._id == "ss"
    # notes are no longer searched
    assert api._find_by_title(lib, "better than", "novelfire.net") is None
    # same title on the same site twice (novel + manhwa) -> ambiguous -> no guess
    assert api._find_by_title(lib, "Omniscient Reader's Viewpoint", "flamecomics.xyz") is None
    # other site's entries are ignored; manual entries (no URL) are allowed
    assert api._find_by_title(lib, "Renegade Immortal", "novelfire.net") is None
    assert api._find_by_title(lib, "Some Manual Entry", "novelfire.net")._id == "manual"


def test_cors_origin_exact_hosts_only():
    ok = ["chrome-extension://abcdefghijklmnop", "moz-extension://1234-5678",
          "http://localhost", "http://localhost:3000", "http://127.0.0.1:8080"]
    bad = ["http://localhost.attacker.example", "http://127.0.0.1.nip.io",
           "https://evil.example", "null", "", "chrome-extension://"]
    for o in ok:
        assert api._cors_origin(o) == o, o
    for o in bad:
        assert api._cors_origin(o) is None, o
