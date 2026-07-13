"""Hub application static asset behaviour."""

from __future__ import annotations

import httpx

from printguard.server.app import ASSET_CACHE_CONTROL, REVALIDATE_CACHE_CONTROL, WebStaticFiles


async def test_web_static_files_revalidate_html_and_cache_hashed_assets(tmp_path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "assets" / "index-abc123.js").write_text("export {}")
    transport = httpx.ASGITransport(app=WebStaticFiles(directory=tmp_path, html=True))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        html = await client.get("/")
        asset = await client.get("/assets/index-abc123.js")
        unchanged = await client.get("/", headers={"If-None-Match": html.headers["etag"]})

    assert html.headers["cache-control"] == REVALIDATE_CACHE_CONTROL
    assert asset.headers["cache-control"] == ASSET_CACHE_CONTROL
    assert unchanged.status_code == 304 and unchanged.headers["cache-control"] == REVALIDATE_CACHE_CONTROL
    assert "etag" in html.headers and "etag" in asset.headers
