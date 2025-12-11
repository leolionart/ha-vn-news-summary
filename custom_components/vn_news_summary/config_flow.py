import voluptuous as vol
import requests
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, CONF_API_KEY, CONF_AI_PROVIDER, CONF_SOURCES, 
    CONF_UPDATE_INTERVAL, CONF_PROMPT, CONF_MODEL, CONF_SUMMARY_LENGTH,
    DEFAULT_SOURCES, DEFAULT_INTERVAL, DEFAULT_PROMPT, DEFAULT_MODEL,
    LENGTH_OPTIONS, DEFAULT_LENGTH
)

FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

def get_groq_models(api_key):
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
    except: pass
    return FALLBACK_MODELS

class VnNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="VN News AI", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_AI_PROVIDER, default="gemini"): vol.In(["gemini", "groq"]),
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_SOURCES, default=DEFAULT_SOURCES): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_INTERVAL): int,
            vol.Optional(CONF_SUMMARY_LENGTH, default=DEFAULT_LENGTH): vol.In(LENGTH_OPTIONS), # <--- Chọn độ dài
            vol.Optional(CONF_PROMPT, default=DEFAULT_PROMPT): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return VnNewsOptionsFlowHandler(config_entry)

class VnNewsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        config = self.config_entry.data
        options = self.config_entry.options
        
        # Lấy giá trị hiện tại
        cur_api = options.get(CONF_API_KEY, config.get(CONF_API_KEY))
        cur_prov = options.get(CONF_AI_PROVIDER, config.get(CONF_AI_PROVIDER, "gemini"))
        cur_mod = options.get(CONF_MODEL, config.get(CONF_MODEL, DEFAULT_MODEL))
        cur_len = options.get(CONF_SUMMARY_LENGTH, config.get(CONF_SUMMARY_LENGTH, DEFAULT_LENGTH))

        # List model logic
        model_list = FALLBACK_MODELS
        if cur_prov == "groq" and cur_api:
            fetched = await self.hass.async_add_executor_job(get_groq_models, cur_api)
            if fetched: 
                model_list = fetched
                if cur_mod not in model_list: model_list.append(cur_mod)

        schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=cur_api): str,
            vol.Required(CONF_AI_PROVIDER, default=cur_prov): vol.In(["gemini", "groq"]),
            vol.Optional(CONF_MODEL, default=cur_mod): vol.In(sorted(model_list)),
            
            # Menu chọn độ dài mới
            vol.Required(CONF_SUMMARY_LENGTH, default=cur_len): vol.In(LENGTH_OPTIONS),
            
            vol.Required(CONF_SOURCES, default=options.get(CONF_SOURCES, config.get(CONF_SOURCES, DEFAULT_SOURCES))): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=options.get(CONF_UPDATE_INTERVAL, config.get(CONF_UPDATE_INTERVAL, DEFAULT_INTERVAL))): int,
            vol.Required(CONF_PROMPT, default=options.get(CONF_PROMPT, config.get(CONF_PROMPT, DEFAULT_PROMPT))): str,
        })

        return self.async_show_form(step_id="init", data_schema=schema)