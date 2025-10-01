"""
Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DeepgramTTSApiClient
from .api_models import DeepgramModelsClient
from .const import DOMAIN, LOGGER
from .stream_processor import DeepgramStreamProcessor
from .tts import DeepgramTtsEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry

PLATFORMS: list[Platform] = [
    Platform.TTS,
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up the integration."""
    api_key = entry.data.get(CONF_API_KEY) or entry.data.get("api_key")
    if not api_key:
        raise ValueError("No API key found in config entry data (neither CONF_API_KEY nor 'api_key').")
    client = DeepgramTTSApiClient(
        api_key=api_key,
        session=async_get_clientsession(hass),
    )
    models_client = DeepgramModelsClient(async_get_clientsession(hass))
    models_data = await models_client.fetch_models()
    client._models_cache = models_data.get("tts", [])
    hass.data.setdefault(DOMAIN, {})
    processor = DeepgramStreamProcessor(client)
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "processor": processor,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
