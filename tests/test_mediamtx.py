"""Hub stream routing through MediaMTX."""

from __future__ import annotations

import json

import httpx
import pytest

from printguard.server.mediamtx import MediaMTX, pull_source


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


async def test_managed_pull_sources_start_on_demand() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        await MediaMTX("http://mediamtx", "rtsp://mediamtx", client).ensure_path("camera", "rtsp://camera/live")

    assert json.loads(requests[0].content) == {
        "source": "rtsp://camera/live",
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "30s",
        "sourceOnDemandCloseAfter": "10s",
    }
