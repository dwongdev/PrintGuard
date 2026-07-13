"""Desktop app launch behaviour."""

from __future__ import annotations

from printguard.server import desktop


def test_webview_url_changes_with_version(monkeypatch) -> None:
    monkeypatch.setattr(desktop.metadata, "version", lambda _: "2.3.3")
    assert desktop._webview_url(8123) == "http://localhost:8123/?v=2.3.3"
