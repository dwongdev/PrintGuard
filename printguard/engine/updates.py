"""Checks GitHub Releases for a newer published version of PrintGuard.

The project publishes every CHANGELOG.md section verbatim as its GitHub
release notes, so the releases list yields both the version comparison and
the changelog to show in one request. Hub mode runs this against
``platform.update_repo``; local mode is always the latest GitHub Pages build
and leaves ``update_repo`` unset, so it never calls out.
"""

from __future__ import annotations

import time
from typing import Any

from .adapters import HttpFn

RELEASES_URL = "https://api.github.com/repos/{repo}/releases"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
TIMEOUT_S = 15.0


async def fetch_updates(http: HttpFn, repo: str, current: str, asset: str | None = None) -> dict[str, Any]:
    """Returns the update status for ``current`` against ``repo``'s releases.

    Args:
        http: Platform HTTP function.
        repo: GitHub ``owner/name`` to read releases from.
        current: The running version (a PEP 440 string).
        asset: Release asset filename this deployment updates with, or None
            when the deployment updates outside the app.

    Returns:
        A status dict with ``current``, ``latest``, ``available``, the
        ``releases`` newer than ``current`` (newest first, each carrying its
        changelog ``notes`` and ``url``) and ``download`` - the latest
        release's URL for ``asset``, or None.

    Raises:
        RuntimeError: If GitHub does not return a releases list.
    """
    from packaging.version import InvalidVersion, Version

    status, body = await http("GET", RELEASES_URL.format(repo=repo), headers=HEADERS, timeout=TIMEOUT_S)
    if status != 200 or not isinstance(body, list):
        raise RuntimeError(f"GitHub returned {status}")
    current_version = Version(current)
    newer: list[dict[str, Any]] = []
    assets_by_version: dict[str, list[dict[str, Any]]] = {}
    for release in body:
        if release.get("draft") or release.get("prerelease"):
            continue
        try:
            version = Version((release.get("tag_name") or "").lstrip("v"))
        except InvalidVersion:
            continue
        if version.is_prerelease or version <= current_version:
            continue
        assets_by_version[str(version)] = release.get("assets") or []
        newer.append(
            {
                "version": str(version),
                "name": release.get("name") or str(version),
                "notes": (release.get("body") or "").strip(),
                "url": release.get("html_url") or f"https://github.com/{repo}/releases/tag/v{version}",
                "published_at": release.get("published_at"),
            }
        )
    newer.sort(key=lambda release: Version(release["version"]), reverse=True)
    download = None
    if asset and newer:
        latest_assets = assets_by_version[newer[0]["version"]]
        download = next((a.get("browser_download_url") for a in latest_assets if a.get("name") == asset), None)
    return {
        "current": current,
        "latest": newer[0]["version"] if newer else current,
        "available": bool(newer),
        "releases": newer,
        "download": download,
        "checked_at": time.time(),
        "releases_url": f"https://github.com/{repo}/releases",
    }
