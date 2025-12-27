DOMAIN = "vn_news_summary"
CONF_API_KEY = "api_key"
CONF_AI_PROVIDER = "ai_provider"
CONF_SOURCES = "sources"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_PROMPT = "prompt"
CONF_MODEL = "model"
CONF_SUMMARY_LENGTH = "summary_length" # <--- Mới
CONF_BASE_URL = "base_url"
CONF_MAX_ARTICLES = "max_articles"
CONF_INCLUDE_KEYWORDS = "include_keywords"
CONF_EXCLUDE_KEYWORDS = "exclude_keywords"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_AI_TIMEOUT = "ai_timeout"
CONF_AI_RETRY = "ai_retry"
CONF_FALLBACK_MODEL = "fallback_model"

DEFAULT_SOURCES = "https://vnexpress.net/rss/tin-moi-nhat.rss"
DEFAULT_INTERVAL = 60
DEFAULT_PROMPT = "Văn phong biên tập viên tin tức, nghiêm túc, dễ hiểu."
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_OPENAI_MODEL = "gemini-2.0-flash"
DEFAULT_MAX_ARTICLES = 5
DEFAULT_INCLUDE_KEYWORDS = ""
DEFAULT_EXCLUDE_KEYWORDS = "tử vong, chết, tai nạn, giết, hiếp, thảm sát, bắt giữ, ma túy, mại dâm"
DEFAULT_QUIET_START = "22:00"
DEFAULT_QUIET_END = "06:00"
DEFAULT_AI_TIMEOUT = 60
DEFAULT_AI_RETRY = 2
DEFAULT_FALLBACK_MODEL = ""

# Các tùy chọn độ dài
LENGTH_OPTIONS = [
    "Ngắn gọn (3 câu - Khoảng 80 từ)",
    "Tiêu chuẩn (Khoảng 150 từ)",
    "Chi tiết (Khoảng 300 từ)",
    "Phân tích sâu (Khoảng 500 từ)"
]
DEFAULT_LENGTH = "Tiêu chuẩn (Khoảng 150 từ)"