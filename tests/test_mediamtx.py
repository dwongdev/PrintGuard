"""Hub stream routing through MediaMTX."""

from __future__ import annotations

import pytest

from printguard.server.mediamtx import pull_source


@pytest.mark.parametrize(
    "url, pulled",
    [
        ("rtsp://cam:8554/live", "rtsp://cam:8554/live"),
        ("rtsps://cam:322/live", "rtsps://cam:322/live"),
        ("rtmp://cam/live", "rtmp://cam/live"),
        ("http://pi/webcam/?action=stream", None),
        ("https://pi/webcam/?action=stream", None),
        ("whep://pi:8889/cam/whep", "whep://pi:8889/cam/whep"),
        ("wheps://pi:8889/cam/whep", "wheps://pi:8889/cam/whep"),
        ("whep://pi:1984/api/webrtc?src=chamber", "whep://pi:1984/api/webrtc?src=chamber"),
        ("http://pi:8889/cam/whep", "whep://pi:8889/cam/whep"),
        ("https://pi:8889/cam/whep", "wheps://pi:8889/cam/whep"),
    ],
)
def test_pull_source_routes_urls(url: str, pulled: str | None) -> None:
    assert pull_source(url) == pulled


@pytest.mark.parametrize("url", ["webrtc://pi/cam", "http://pi/webcam/webrtc", "whip://pi/cam"])
def test_pull_source_rejects_non_whep_webrtc(url: str) -> None:
    with pytest.raises(ValueError, match="does not expose WHEP"):
        pull_source(url)
