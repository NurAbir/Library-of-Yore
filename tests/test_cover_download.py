"""download_image: first the image's own URL as Referer, then (if given) the page's."""
import io

import pytest
import requests
from PIL import Image

from utils import helpers


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 6), "red").save(buf, format="PNG")
    return buf.getvalue()


class _Resp:
    def __init__(self, status, content=b""):
        self.status_code, self.content = status, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


IMG, PAGE = "https://cdn.example/cover.jpg", "https://mangafire.to/title/m2wxz-x"


def _patch(monkeypatch, statuses_by_referer):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(headers["Referer"])
        status = statuses_by_referer.get(headers["Referer"], 403)
        return _Resp(status, _png() if status < 400 else b"")

    monkeypatch.setattr(helpers.requests, "get", fake_get)
    return calls


def test_the_images_own_url_is_tried_first_and_enough_when_it_works(monkeypatch):
    calls = _patch(monkeypatch, {IMG: 200})
    assert helpers.download_image(IMG, fallback_referer=PAGE)[:2] == b"\xff\xd8"      # JPEG
    assert calls == [IMG]


def test_a_refused_download_is_retried_with_the_page_as_referer(monkeypatch):
    calls = _patch(monkeypatch, {IMG: 403, PAGE: 200})
    assert helpers.download_image(IMG, fallback_referer=PAGE)[:2] == b"\xff\xd8"
    assert calls == [IMG, PAGE]


def test_without_a_fallback_the_original_error_is_raised(monkeypatch):
    calls = _patch(monkeypatch, {})
    with pytest.raises(requests.HTTPError):
        helpers.download_image(IMG)
    assert calls == [IMG]


def test_both_attempts_failing_raises(monkeypatch):
    calls = _patch(monkeypatch, {})
    with pytest.raises(requests.HTTPError):
        helpers.download_image(IMG, fallback_referer=PAGE)
    assert calls == [IMG, PAGE]
