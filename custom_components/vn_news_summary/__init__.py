import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # Forward setup tới sensor
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Đăng ký listener để reload khi thay đổi cấu hình (Options Flow)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Đăng ký Service: vn_news_summary.read_news
    async def handle_read_news(call: ServiceCall):
        entity_id = call.data.get("entity_id") # Loa nào
        tts_service = call.data.get("tts_service", "tts.google_translate_say") # Dùng TTS nào
        
        # Lấy nội dung từ sensor
        sensor_state = hass.states.get("sensor.vn_news_ai_summary")
        if sensor_state and "full_summary" in sensor_state.attributes:
            message = sensor_state.attributes["full_summary"]
        else:
            message = "Chưa có nội dung tin tức."

        # Gọi service TTS của Hass
        await hass.services.async_call(
            domain=tts_service.split(".")[0],
            service=tts_service.split(".")[1],
            service_data={
                "entity_id": entity_id,
                "message": message
            }
        )

    hass.services.async_register(DOMAIN, "read_news", handle_read_news)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
