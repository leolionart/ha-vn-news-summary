import logging
import requests
import feedparser
import re
import json
from datetime import timedelta

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.components.sensor import SensorEntity

from .const import (
    DOMAIN, CONF_API_KEY, CONF_AI_PROVIDER, CONF_SOURCES, 
    CONF_UPDATE_INTERVAL, CONF_PROMPT, CONF_MODEL, CONF_SUMMARY_LENGTH, 
    DEFAULT_MODEL, DEFAULT_LENGTH
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data.copy()
    if config_entry.options:
        config.update(config_entry.options)
    
    api_key = config.get(CONF_API_KEY)
    provider = config.get(CONF_AI_PROVIDER, "gemini")
    model_name = config.get(CONF_MODEL, DEFAULT_MODEL)
    
    # Lấy cấu hình độ dài
    summary_len = config.get(CONF_SUMMARY_LENGTH, DEFAULT_LENGTH)

    raw_sources = config.get(CONF_SOURCES, "")
    sources = []
    if raw_sources:
        sources = [s.strip() for s in re.split(r'[\n\s,]+', raw_sources) if s.strip()]
        
    interval = config.get(CONF_UPDATE_INTERVAL, 60)
    user_style = config.get(CONF_PROMPT, "") 

    async def async_update_data():
        return await hass.async_add_executor_job(
            fetch_and_process_json, api_key, provider, sources, user_style, model_name, summary_len
        )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="vn_news_sensor",
        update_method=async_update_data,
        update_interval=timedelta(minutes=interval),
    )

    await coordinator.async_config_entry_first_refresh()

    sensors = []
    for i in range(20):
        sensors.append(VnNewsChildSensor(coordinator, i))
    async_add_entities(sensors, True)

class VnNewsChildSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, index):
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"vn_news_article_{index + 1}"
        self.entity_id = f"sensor.vn_news_{index + 1:02d}"
        self._attr_name = f"VN News {index + 1}"
        self._attr_icon = "mdi:newspaper"

    @property
    def state(self):
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > self._index:
            # Cắt ngắn state để không vi phạm giới hạn 255 ký tự của Hass
            return data[self._index].get('summary', 'Lỗi')[:200] + "..."
        return "Trống"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > self._index:
            item = data[self._index]
            return {
                "full_summary": item.get('summary', ''), # Đây là nội dung FULL dài (để đọc loa)
                "title": item.get('title', ''),
                "source": "AI Summary"
            }
        return {"status": "No Data"}

def fetch_and_process_json(api_key, provider, sources, user_style, model_name, summary_len):
    if not sources: return []

    # 1. Chuyển đổi lựa chọn độ dài thành hướng dẫn cho AI
    length_instruction = "khoảng 150 từ" # mặc định
    if "Ngắn" in summary_len:
        length_instruction = "thật ngắn gọn, súc tích, khoảng 3 câu (80 từ)"
    elif "Chi tiết" in summary_len:
        length_instruction = "chi tiết, đầy đủ các ý chính, khoảng 300 từ"
    elif "Phân tích" in summary_len: # Rất dài
        length_instruction = "rất chi tiết, phân tích sâu, khoảng 500 từ"

    all_titles = []
    for url in sources:
        if len(url) < 10: continue
        try:
            if "tuoitre.vn" in url and "rss.htm" in url:
                url = "https://tuoitre.vn/rss/tin-moi-nhat.rss"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                t = entry.get('title', '').strip()
                if t: all_titles.append(t)
        except: pass

    if not all_titles: return []
    top_titles = all_titles[:20]
    titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(top_titles)])

    # 2. PROMPT VỚI ĐỘ DÀI TÙY CHỈNH
    json_prompt = (
        f"Dưới đây là danh sách tiêu đề báo:\n{titles_text}\n\n"
        f"Yêu cầu: Hãy đóng vai biên tập viên, tóm tắt nội dung từng tin.\n"
        f"- Phong cách: {user_style}.\n"
        f"- Độ dài mỗi tin: {length_instruction}.\n" # <--- Điểm quan trọng
        f"QUAN TRỌNG: Chỉ trả về kết quả JSON Array chuẩn ([...]). "
        f"Cấu trúc: [{{ \"id\": 1, \"title\": \"Tiêu đề\", \"summary\": \"Nội dung tóm tắt...\" }}, ...]"
    )

    response_text = ""
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            resp = requests.post(
                url, 
                json={"contents": [{"parts": [{"text": json_prompt}]}]}, 
                headers={'Content-Type': 'application/json'},
                timeout=40 # Tăng timeout vì bài dài AI viết lâu hơn
            )
            if resp.status_code == 200:
                response_text = resp.json()['candidates'][0]['content']['parts'][0]['text']

        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            if model_name == "llama3-8b-8192": model_name = "llama-3.1-8b-instant"
            
            resp = requests.post(
                url,
                json={
                    "messages": [{"role": "user", "content": json_prompt}],
                    "model": model_name,
                    "response_format": {"type": "json_object"}
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=40
            )
            if resp.status_code == 200:
                response_text = resp.json()['choices'][0]['message']['content']

        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        match_obj = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match_obj:
            json_obj = json.loads(match_obj.group(0))
            for key in json_obj:
                if isinstance(json_obj[key], list): return json_obj[key]
            
    except Exception as e:
        _LOGGER.error(f"Lỗi AI JSON: {e}")
    
    return []