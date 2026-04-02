"""DataUpdateCoordinator for the ZTE MC889 modem."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, POLL_FIELDS
from .zte_api import ZteAuthError, ZteClient, ZteError, ZteLockoutError

_LOGGER = logging.getLogger(__name__)


class ZteMC889Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from the ZTE MC889 modem."""

    def __init__(self, hass: HomeAssistant, host: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"ZTE MC889 ({host})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host = host
        self._client = ZteClient(
            host=host,
            password=password,
            session_file=hass.config.path(".zte_mc889_session"),
            timeout=10,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(
                self._client.get, POLL_FIELDS
            )
        except ZteLockoutError as err:
            raise UpdateFailed(f"Modem locked out: {err}") from err
        except ZteAuthError as err:
            raise UpdateFailed(f"Auth failed: {err}") from err
        except ZteError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Connection error: {err}") from err
