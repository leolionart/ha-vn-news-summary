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
    CONF_UPDATE_INTERVAL, CONF_PROMPT, CONF_MODEL, CONF_SUMMARY_LENGTH, CONF_BASE_URL,
    DEFAULT_MODEL, DEFAULT_LENGTH
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# Danh sách từ khóa mặc định cần loại bỏ (Bạn có thể sửa trực tiếp ở đây hoặc đưa vào Config Flow sau)
BAD_KEYWORDS = ["tử vong", "chết", "tai nạn", "giết", "hiếp", "thảm sát", "bắt giữ", "ma túy", "mại dâm"]

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data.copy()
    if config_entry.options:
        config.update(config_entry.options)
    
    api_key = config.get(CONF_API_KEY)
    provider = config.get(CONF_AI_PROVIDER, "gemini")
    model_name = config.get(CONF_MODEL, DEFAULT_MODEL)
    summary_len = config.get(CONF_SUMMARY_LENGTH, DEFAULT_LENGTH)
    user_style = config.get(CONF_PROMPT, "")
    base_url = config.get(CONF_BASE_URL, "")

    raw_sources = config.get(CONF_SOURCES, "")
    sources = []
    if raw_sources:
        sources = [s.strip() for s in re.split(r'[\n\s,]+', raw_sources) if s.strip()]
    
    interval = config.get(CONF_UPDATE_INTERVAL, 60)

    async def async_update_data():
        return await hass.async_add_executor_job(
            fetch_and_process_json, api_key, provider, sources, user_style, model_name, summary_len, base_url
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
    # Tạo 20 sensor con
    for i in range(20):
        sensors.append(VnNewsChildSensor(coordinator, i))
    
    # Tạo thêm 1 Sensor tổng hợp (Podcast)
    sensors.append(VnNewsPodcastSensor(coordinator))
    
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
            return data[self._index].get('summary', 'Lỗi')[:200] + "..."
        return "Trống"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > self._index:
            item = data[self._index]
            return {
                "full_summary": item.get('summary', ''),
                "title": item.get('title', ''),
                "link": item.get('link', ''), # Link gốc bài báo
            }
        return {"status": "No Data"}

    @property
    def entity_picture(self):
        """Hiển thị ảnh thumbnail bài báo"""
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > self._index:
            return data[self._index].get('image', None)
        return None

class VnNewsPodcastSensor(CoordinatorEntity, SensorEntity):
    """Sensor đặc biệt chứa nội dung gộp để đọc 1 lần"""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "vn_news_podcast_master"
        self.entity_id = "sensor.vn_news_podcast"
        self._attr_name = "VN News Podcast Mode"
        self._attr_icon = "mdi:podcast"

    @property
    def state(self):
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > 0:
            return "Sẵn sàng phát"
        return "Không có tin"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if isinstance(data, list) and len(data) > 0:
            # Gộp tất cả tóm tắt thành 1 văn bản dài
            intro = "Chào bạn, đây là tổng hợp tin tức mới nhất. "
            content = " ".join([f"Tin số {i+1}: {item.get('summary', '')}. " for i, item in enumerate(data)])
            outro = "Đó là toàn bộ tin tức đáng chú ý. Chúc bạn một ngày tốt lành."
            return {"podcast_content": intro + content + outro}
        return {"podcast_content": "Chưa có dữ liệu tin tức."}

def fetch_and_process_json(api_key, provider, sources, user_style, model_name, summary_len, base_url):
    if not sources: return []

    length_instruction = "khoảng 150 từ"
    if "Ngắn" in summary_len: length_instruction = "ngắn gọn, khoảng 80 từ"
    elif "Chi tiết" in summary_len: length_instruction = "chi tiết, khoảng 300 từ"

    articles_to_send = []
    
    # 1. TẢI RSS VÀ LỌC TIN (FILTER + IMAGE EXTRACT)
    for url in sources:
        if len(url) < 10: continue
        try:
            if "tuoitre.vn" in url and "rss.htm" in url: url = "https://tuoitre.vn/rss/tin-moi-nhat.rss"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content)
            
            for entry in feed.entries:
                t = entry.get('title', '').strip()
                link = entry.get('link', '')
                desc = entry.get('description', '')
                
                # A. Lọc từ khóa tiêu cực
                if any(bad in t.lower() for bad in BAD_KEYWORDS):
                    continue # Bỏ qua tin này
                
                # B. Lấy ảnh từ description
                img_url = None
                img_match = re.search(r'src="([^"]+jpg|[^"]+png|[^"]+jpeg)"', desc)
                if img_match:
                    img_url = img_match.group(1)
                
                # Chỉ lấy tối đa 20 tin
                if len(articles_to_send) < 20:
                    articles_to_send.append({
                        "original_title": t,
                        "link": link,
                        "image": img_url
                    })
        except: pass

    if not articles_to_send: return []

    # Tạo list title để gửi AI
    titles_text = "\n".join([f"{i+1}. {item['original_title']}" for i, item in enumerate(articles_to_send)])

    # 2. PROMPT
    json_prompt = (
        f"Dưới đây là danh sách tiêu đề báo:\n{titles_text}\n\n"
        f"Yêu cầu: Đóng vai biên tập viên, tóm tắt từng tin.\n"
        f"- Phong cách: {user_style}.\n"
        f"- Độ dài: {length_instruction}.\n"
        f"QUAN TRỌNG: Trả về JSON Array đúng thứ tự đầu vào. "
        f"Cấu trúc: [{{ \"summary\": \"Nội dung tóm tắt...\" }}, ...]"
    )

    response_text = ""
    try:
        # Gọi Gemini/Groq (Giữ nguyên logic cũ)
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            resp = requests.post(
                url, 
                json={"contents": [{"parts": [{"text": json_prompt}]}]}, 
                headers={'Content-Type': 'application/json'},
                timeout=40
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

        elif provider == "openai":
            # Sử dụng Base URL nếu có, ngược lại dùng mặc định
            url = base_url if base_url else "https://api.openai.com/v1/chat/completions"
            # Chuẩn hóa URL nếu người dùng quên /v1/chat/completions trong base url ngắn gọn (tuỳ chọn, ở đây giả định base_url là full endpoint hoặc base path)
            # Tuy nhiên, thông thường base_url trong các thư viện là "https://api.openai.com/v1", còn endpoint cụ thể ghép sau.
            # Để đơn giản cho user, ta quy ước user nhập FULL endpoint hoặc ta ghép.
            # Cách an toàn: Nếu base_url không chứa "chat/completions", ta nối vào (logic mềm dẻo).
            if "chat/completions" not in url:
                url = url.rstrip('/') + "/chat/completions"

            resp = requests.post(
                url,
                json={
                    "messages": [{"role": "user", "content": json_prompt}],
                    "model": model_name,
                    # OpenAI hỗ trợ response_format={"type": "json_object"} với các model mới
                    # Để an toàn, ta chỉ dùng nếu model hỗ trợ, hoặc cứ gửi, nếu lỗi thì fallback (nhưng ở đây cứ gửi)
                    # Lưu ý: OpenAI yêu cầu prompt phải có chữ "JSON" nếu dùng mode json_object. Prompt của ta đã có.
                    "response_format": {"type": "json_object"}
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=40
            )
            if resp.status_code == 200:
                response_text = resp.json()['choices'][0]['message']['content']
            else:
                 _LOGGER.error(f"OpenAI Error {resp.status_code}: {resp.text}")

        # 3. GHÉP DỮ LIỆU AI VÀO DỮ LIỆU GỐC (ẢNH, LINK)
        ai_data = []
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            ai_data = json.loads(match.group(0))
        else:
            match_obj = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match_obj:
                json_obj = json.loads(match_obj.group(0))
                for key in json_obj:
                    if isinstance(json_obj[key], list): ai_data = json_obj[key]; break
        
        # Merge kết quả
        final_result = []
        for i, article in enumerate(articles_to_send):
            summary = "Không có tóm tắt"
            if i < len(ai_data):
                summary = ai_data[i].get('summary', '')
            
            final_result.append({
                "title": article['original_title'],
                "link": article['link'],
                "image": article['image'],
                "summary": summary
            })
            
        return final_result
            
    except Exception as e:
        _LOGGER.error(f"Lỗi AI JSON: {e}")
    
    return []