import voluptuous as vol
import requests
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from .const import (
    DOMAIN, CONF_API_KEY, CONF_AI_PROVIDER, CONF_SOURCES,
    CONF_UPDATE_INTERVAL, CONF_PROMPT, CONF_MODEL, CONF_SUMMARY_LENGTH, CONF_BASE_URL,
    CONF_MAX_ARTICLES, CONF_INCLUDE_KEYWORDS, CONF_EXCLUDE_KEYWORDS,
    CONF_QUIET_START, CONF_QUIET_END, CONF_AI_TIMEOUT, CONF_AI_RETRY, CONF_FALLBACK_MODEL,
    DEFAULT_SOURCES, DEFAULT_INTERVAL, DEFAULT_PROMPT, DEFAULT_MODEL,
    DEFAULT_MAX_ARTICLES, DEFAULT_INCLUDE_KEYWORDS, DEFAULT_EXCLUDE_KEYWORDS,
    DEFAULT_QUIET_START, DEFAULT_QUIET_END, DEFAULT_AI_TIMEOUT, DEFAULT_AI_RETRY, DEFAULT_FALLBACK_MODEL,
    LENGTH_OPTIONS, DEFAULT_LENGTH, DEFAULT_OPENAI_MODEL
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

def get_openai_models(api_key, base_url):
    """Fetch models from OpenAI-compatible API endpoint."""
    try:
        # Construct models endpoint URL
        if base_url:
            url = base_url.rstrip('/')
            # Remove /chat/completions if present
            if url.endswith('/chat/completions'):
                url = url.rsplit('/chat/completions', 1)[0]
            # Ensure /models endpoint
            if not url.endswith('/models'):
                url = url.rstrip('/') + '/models'
        else:
            url = "https://api.openai.com/v1/models"

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [model["id"] for model in data.get("data", [])]
            if models:
                return models
    except: pass
    # Fallback to common OpenAI models
    return ["gemini-2.0-flash", "gemini-2.5-flash", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]

class VnNewsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="VN News AI", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_AI_PROVIDER, default="gemini"): vol.In(["gemini", "groq", "openai"]),
            vol.Required(CONF_API_KEY): str,
            vol.Optional(CONF_BASE_URL): str,
            vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): SelectSelector(
                SelectSelectorConfig(
                    options=sorted(FALLBACK_MODELS),
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_SOURCES, default=DEFAULT_SOURCES): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_INTERVAL): int,
            vol.Optional(CONF_SUMMARY_LENGTH, default=DEFAULT_LENGTH): vol.In(LENGTH_OPTIONS),
            vol.Optional(CONF_PROMPT, default=DEFAULT_PROMPT): str,
            # Advanced settings
            vol.Optional(CONF_MAX_ARTICLES, default=DEFAULT_MAX_ARTICLES): int,
            vol.Optional(CONF_INCLUDE_KEYWORDS, default=DEFAULT_INCLUDE_KEYWORDS): str,
            vol.Optional(CONF_EXCLUDE_KEYWORDS, default=DEFAULT_EXCLUDE_KEYWORDS): str,
            vol.Optional(CONF_QUIET_START, default=DEFAULT_QUIET_START): str,
            vol.Optional(CONF_QUIET_END, default=DEFAULT_QUIET_END): str,
            vol.Optional(CONF_AI_TIMEOUT, default=DEFAULT_AI_TIMEOUT): int,
            vol.Optional(CONF_AI_RETRY, default=DEFAULT_AI_RETRY): int,
            vol.Optional(CONF_FALLBACK_MODEL, default=DEFAULT_FALLBACK_MODEL): SelectSelector(
                SelectSelectorConfig(
                    options=sorted(FALLBACK_MODELS),
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
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
        cur_api = options.get(CONF_API_KEY, config.get(CONF_API_KEY)) or ""
        cur_prov = options.get(CONF_AI_PROVIDER, config.get(CONF_AI_PROVIDER, "gemini")) or "gemini"
        cur_mod = options.get(CONF_MODEL, config.get(CONF_MODEL, DEFAULT_MODEL)) or DEFAULT_MODEL
        cur_len = options.get(CONF_SUMMARY_LENGTH, config.get(CONF_SUMMARY_LENGTH, DEFAULT_LENGTH)) or DEFAULT_LENGTH
        cur_base_url = options.get(CONF_BASE_URL, config.get(CONF_BASE_URL, "")) or ""

        # List model logic
        model_list = list(FALLBACK_MODELS)  # Copy to avoid modifying original

        if cur_prov == "openai" and cur_api:
            # Fetch models from OpenAI-compatible API
            fetched = await self.hass.async_add_executor_job(get_openai_models, cur_api, cur_base_url)
            if fetched:
                model_list = fetched
            # Set default model for OpenAI if current is Groq model
            if not cur_mod or cur_mod == DEFAULT_MODEL or cur_mod in FALLBACK_MODELS:
                cur_mod = DEFAULT_OPENAI_MODEL
            # Ensure current model is in list
            if cur_mod and cur_mod not in model_list:
                model_list.append(cur_mod)

        elif cur_prov == "groq" and cur_api:
            fetched = await self.hass.async_add_executor_job(get_groq_models, cur_api)
            if fetched:
                model_list = fetched
                if cur_mod and cur_mod not in model_list:
                    model_list.append(cur_mod)

        # Ensure model_list is never empty
        if not model_list:
            model_list = list(FALLBACK_MODELS)

        # Logic dynamic schema cho Model (Sử dụng SelectSelector với custom_value=True)
        # Cho phép user chọn từ list HOẶC nhập tay bất kỳ string nào
        model_selector = SelectSelector(
            SelectSelectorConfig(
                options=sorted(model_list),
                custom_value=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

        # Get current advanced settings - ensure proper defaults
        cur_max_articles = options.get(CONF_MAX_ARTICLES, config.get(CONF_MAX_ARTICLES, DEFAULT_MAX_ARTICLES)) or DEFAULT_MAX_ARTICLES
        cur_include_kw = options.get(CONF_INCLUDE_KEYWORDS, config.get(CONF_INCLUDE_KEYWORDS, DEFAULT_INCLUDE_KEYWORDS)) or ""
        cur_exclude_kw = options.get(CONF_EXCLUDE_KEYWORDS, config.get(CONF_EXCLUDE_KEYWORDS, DEFAULT_EXCLUDE_KEYWORDS)) or ""
        cur_quiet_start = options.get(CONF_QUIET_START, config.get(CONF_QUIET_START, DEFAULT_QUIET_START)) or DEFAULT_QUIET_START
        cur_quiet_end = options.get(CONF_QUIET_END, config.get(CONF_QUIET_END, DEFAULT_QUIET_END)) or DEFAULT_QUIET_END
        cur_timeout = options.get(CONF_AI_TIMEOUT, config.get(CONF_AI_TIMEOUT, DEFAULT_AI_TIMEOUT)) or DEFAULT_AI_TIMEOUT
        cur_retry = options.get(CONF_AI_RETRY, config.get(CONF_AI_RETRY, DEFAULT_AI_RETRY)) or DEFAULT_AI_RETRY
        cur_fallback = options.get(CONF_FALLBACK_MODEL, config.get(CONF_FALLBACK_MODEL, DEFAULT_FALLBACK_MODEL)) or ""

        # Fallback model selector - include empty option
        fallback_options = [""] + sorted(model_list)  # Empty string = no fallback
        fallback_selector = SelectSelector(
            SelectSelectorConfig(
                options=fallback_options,
                custom_value=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

        schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=cur_api): str,
            vol.Required(CONF_AI_PROVIDER, default=cur_prov): vol.In(["gemini", "groq", "openai"]),
            vol.Optional(CONF_BASE_URL, default=cur_base_url): str,
            vol.Optional(CONF_MODEL, default=cur_mod): model_selector,

            # Menu chọn độ dài mới
            vol.Required(CONF_SUMMARY_LENGTH, default=cur_len): vol.In(LENGTH_OPTIONS),

            vol.Required(CONF_SOURCES, default=options.get(CONF_SOURCES, config.get(CONF_SOURCES, DEFAULT_SOURCES))): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=options.get(CONF_UPDATE_INTERVAL, config.get(CONF_UPDATE_INTERVAL, DEFAULT_INTERVAL))): int,
            vol.Required(CONF_PROMPT, default=options.get(CONF_PROMPT, config.get(CONF_PROMPT, DEFAULT_PROMPT))): str,

            # Advanced settings
            vol.Optional(CONF_MAX_ARTICLES, default=cur_max_articles): int,
            vol.Optional(CONF_INCLUDE_KEYWORDS, default=cur_include_kw): str,
            vol.Optional(CONF_EXCLUDE_KEYWORDS, default=cur_exclude_kw): str,
            vol.Optional(CONF_QUIET_START, default=cur_quiet_start): str,
            vol.Optional(CONF_QUIET_END, default=cur_quiet_end): str,
            vol.Optional(CONF_AI_TIMEOUT, default=cur_timeout): int,
            vol.Optional(CONF_AI_RETRY, default=cur_retry): int,
            vol.Optional(CONF_FALLBACK_MODEL, default=cur_fallback): fallback_selector,
        })

        return self.async_show_form(step_id="init", data_schema=schema)
