"""Elegoo integration over the local Centauri and Moonraker protocols.

Elegoo's official Link SDK supports Centauri Carbon 1 and 2, Neptune 4
Pro/Plus/Max, OrangeStorm Giga and other Moonraker printers through one
local-LAN surface. Centauri models use raw WebSocket or MQTT connections,
so this adapter is hub-only; Moonraker models reuse PrintGuard's Klipper
adapter instead of duplicating its HTTP implementation.

Official SDK and model list: https://github.com/ELEGOO-3D/elegoo-link
Centauri Python client: https://github.com/bjan/pycentauri
"""

from __future__ import annotations

from typing import Any

from .base import DeviceAction, DeviceState, DeviceStatus, HttpFn, IntegrationAdapter
from .klipper import KlipperAdapter

_CENTAURI = "centauri"
_MOONRAKER = "moonraker"
_PRINTING = {1, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 29}
_PAUSED = {5, 6}
_IDLE = {0, 7, 8, 9}
_ERROR = {14}
_ACTIONS = {
    DeviceAction.PAUSE: "pause",
    DeviceAction.RESUME: "resume",
    DeviceAction.CANCEL: "stop",
}


class ElegooAdapter(IntegrationAdapter):
    """Controls supported Elegoo FDM printers directly on the local network."""

    id = "elegoo"
    label = "Elegoo"
    docs_url = "https://github.com/ELEGOO-3D/elegoo-link"
    setup_hint = (
        "Centauri Carbon 2 needs LAN Only Mode and its screen access code. "
        "Neptune 4 and OrangeStorm printers use their stock Moonraker service."
    )
    browser_ok = False
    experimental = True
    schema = {
        "type": "object",
        "properties": {
            "family": {
                "type": "string",
                "title": "Printer family",
                "enum": [_CENTAURI, _MOONRAKER],
                "enum_labels": ["Centauri Carbon 1 / 2", "Neptune 4 / OrangeStorm Giga"],
            },
            "host": {"type": "string", "title": "Printer IP or hostname", "placeholder": "192.168.1.80"},
            "access_code": {
                "type": "string",
                "title": "Access code (Centauri Carbon 2 only)",
                "secret": True,
                "placeholder": "Shown under the printer's network settings",
            },
            "api_key": {
                "type": "string",
                "title": "Moonraker API key (optional)",
                "secret": True,
                "placeholder": "Leave blank if unset",
            },
        },
        "required": ["family", "host"],
    }

    def __init__(self) -> None:
        self._moonraker = KlipperAdapter()

    async def fetch_state(self, http: HttpFn, config: dict[str, Any]) -> DeviceState:
        """Reads and normalises the active print state."""
        if self._family(config) == _MOONRAKER:
            return await self._moonraker.fetch_state(http, self._moonraker_config(config))
        printer = await self._connect_centauri(config)
        try:
            status = await printer.status()
        finally:
            await printer.close()
        return DeviceState(
            self._status(status.print_status),
            float(status.progress or 0.0),
            status.filename or None,
        )

    async def send(self, http: HttpFn, config: dict[str, Any], action: DeviceAction) -> None:
        """Pauses, resumes or stops the active print."""
        if self._family(config) == _MOONRAKER:
            await self._moonraker.send(http, self._moonraker_config(config), action)
            return
        printer = await self._connect_centauri(config, enable_control=True)
        try:
            await getattr(printer, _ACTIONS[action])()
        finally:
            await printer.close()

    async def cameras(self, http: HttpFn, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Exposes the built-in Centauri camera or Moonraker webcams."""
        if self._family(config) == _MOONRAKER:
            return await self._moonraker.cameras(http, self._moonraker_config(config))
        printer = await self._connect_centauri(config)
        try:
            port = printer.camera_port
        finally:
            await printer.close()
        return [
            {
                "key": "chamber",
                "name": "Chamber camera",
                "source": {"kind": "url", "url": f"http://{config['host']}:{port}/video"},
            }
        ]

    async def _connect_centauri(self, config: dict[str, Any], *, enable_control: bool = False) -> Any:
        from pycentauri import connect_auto

        return await connect_auto(
            str(config["host"]),
            access_code=str(config.get("access_code") or "") or None,
            enable_control=enable_control,
        )

    def _family(self, config: dict[str, Any]) -> str:
        family = str(config["family"])
        if family not in (_CENTAURI, _MOONRAKER):
            raise ValueError(f"unknown Elegoo printer family {family!r}")
        return family

    def _moonraker_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "base_url": f"http://{config['host']}:7125",
            "api_key": str(config.get("api_key") or ""),
        }

    def _status(self, status: int | None) -> DeviceStatus:
        if status in _PRINTING:
            return DeviceStatus.PRINTING
        if status in _PAUSED:
            return DeviceStatus.PAUSED
        if status in _IDLE:
            return DeviceStatus.IDLE
        if status in _ERROR:
            return DeviceStatus.ERROR
        return DeviceStatus.UNKNOWN
