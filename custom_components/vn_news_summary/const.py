DOMAIN = "vn_news_summary"
CONF_API_KEY = "api_key"
CONF_AI_PROVIDER = "ai_provider"
CONF_SOURCES = "sources"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_PROMPT = "prompt"
CONF_MODEL = "model"
CONF_SUMMARY_LENGTH = "summary_length" # <--- Mới
CONF_BASE_URL = "base_url"

DEFAULT_SOURCES = "https://vnexpress.net/rss/tin-moi-nhat.rss"
DEFAULT_INTERVAL = 60
DEFAULT_PROMPT = "Văn phong biên tập viên tin tức, nghiêm túc, dễ hiểu."
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_OPENAI_MODEL = "gemini-2.0-flash"

# Các tùy chọn độ dài
LENGTH_OPTIONS = [
    "Ngắn gọn (3 câu - Khoảng 80 từ)",
    "Tiêu chuẩn (Khoảng 150 từ)",
    "Chi tiết (Khoảng 300 từ)",
    "Phân tích sâu (Khoảng 500 từ)"
]
DEFAULT_LENGTH = "Tiêu chuẩn (Khoảng 150 từ)"