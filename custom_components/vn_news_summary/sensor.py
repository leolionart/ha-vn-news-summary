import logging
import requests
import feedparser
import re
import json
from datetime import timedelta, datetime

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.components.sensor import SensorEntity

from .const import (
    DOMAIN, CONF_API_KEY, CONF_AI_PROVIDER, CONF_SOURCES,
    CONF_UPDATE_INTERVAL, CONF_PROMPT, CONF_MODEL, CONF_SUMMARY_LENGTH, CONF_BASE_URL,
    CONF_MAX_ARTICLES, CONF_INCLUDE_KEYWORDS, CONF_EXCLUDE_KEYWORDS,
    CONF_QUIET_START, CONF_QUIET_END, CONF_AI_TIMEOUT, CONF_AI_RETRY, CONF_FALLBACK_MODEL,
    DEFAULT_MODEL, DEFAULT_LENGTH,
    DEFAULT_MAX_ARTICLES, DEFAULT_INCLUDE_KEYWORDS, DEFAULT_EXCLUDE_KEYWORDS,
    DEFAULT_QUIET_START, DEFAULT_QUIET_END, DEFAULT_AI_TIMEOUT, DEFAULT_AI_RETRY, DEFAULT_FALLBACK_MODEL
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# Cache để lưu dữ liệu cũ khi API lỗi hoặc trong quiet hours
_LAST_GOOD_DATA = []

def is_quiet_hours(quiet_start: str, quiet_end: str) -> bool:
    """Kiểm tra xem hiện tại có nằm trong giờ im lặng không."""
    try:
        now = datetime.now().time()
        start = datetime.strptime(quiet_start, "%H:%M").time()
        end = datetime.strptime(quiet_end, "%H:%M").time()

        # Xử lý trường hợp qua đêm (22:00 - 06:00)
        if start > end:
            return now >= start or now <= end
        else:
            return start <= now <= end
    except:
        return False

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
        # Hỗ trợ bật/tắt nguồn bằng # ở đầu dòng
        for s in re.split(r'[\n,]+', raw_sources):
            s = s.strip()
            if s and not s.startswith('#') and len(s) > 10:
                sources.append(s)

    interval = config.get(CONF_UPDATE_INTERVAL, 60)

    # Advanced settings
    max_articles = config.get(CONF_MAX_ARTICLES, DEFAULT_MAX_ARTICLES)
    include_keywords = config.get(CONF_INCLUDE_KEYWORDS, DEFAULT_INCLUDE_KEYWORDS)
    exclude_keywords = config.get(CONF_EXCLUDE_KEYWORDS, DEFAULT_EXCLUDE_KEYWORDS)
    quiet_start = config.get(CONF_QUIET_START, DEFAULT_QUIET_START)
    quiet_end = config.get(CONF_QUIET_END, DEFAULT_QUIET_END)
    ai_timeout = config.get(CONF_AI_TIMEOUT, DEFAULT_AI_TIMEOUT)
    ai_retry = config.get(CONF_AI_RETRY, DEFAULT_AI_RETRY)
    fallback_model = config.get(CONF_FALLBACK_MODEL, DEFAULT_FALLBACK_MODEL)

    async def async_update_data():
        return await hass.async_add_executor_job(
            fetch_and_process_json, api_key, provider, sources, user_style, model_name, summary_len, base_url,
            max_articles, include_keywords, exclude_keywords, quiet_start, quiet_end, ai_timeout, ai_retry, fallback_model
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

def fetch_and_process_json(api_key, provider, sources, user_style, model_name, summary_len, base_url,
                           max_articles, include_keywords, exclude_keywords, quiet_start, quiet_end,
                           ai_timeout, ai_retry, fallback_model):
    global _LAST_GOOD_DATA

    if not sources:
        return _LAST_GOOD_DATA if _LAST_GOOD_DATA else []

    # Kiểm tra Quiet Hours - nếu trong giờ im lặng thì trả về cache
    if is_quiet_hours(quiet_start, quiet_end):
        _LOGGER.info("Đang trong giờ im lặng, sử dụng dữ liệu cache")
        return _LAST_GOOD_DATA if _LAST_GOOD_DATA else []

    # Parse keyword filters
    exclude_list = [kw.strip().lower() for kw in exclude_keywords.split(',') if kw.strip()]
    include_list = [kw.strip().lower() for kw in include_keywords.split(',') if kw.strip()]

    length_instruction = "khoảng 150 từ"
    if "Ngắn" in summary_len: length_instruction = "ngắn gọn, khoảng 80 từ"
    elif "Chi tiết" in summary_len: length_instruction = "chi tiết, khoảng 300 từ"
    elif "Phân tích" in summary_len: length_instruction = "phân tích sâu, khoảng 500 từ"

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
                t_lower = t.lower()

                # A. Lọc từ khóa loại trừ (exclude)
                if any(bad in t_lower for bad in exclude_list):
                    continue  # Bỏ qua tin này

                # B. Nếu có include_keywords, chỉ lấy tin chứa từ đó
                if include_list and not any(inc in t_lower for inc in include_list):
                    continue  # Bỏ qua nếu không chứa từ khóa ưu tiên

                # C. Lấy ảnh từ description
                img_url = None
                img_match = re.search(r'src="([^"]+jpg|[^"]+png|[^"]+jpeg)"', desc)
                if img_match:
                    img_url = img_match.group(1)

                # Giới hạn theo max_articles
                if len(articles_to_send) < max_articles:
                    articles_to_send.append({
                        "original_title": t,
                        "link": link,
                        "image": img_url
                    })
        except: pass

    if not articles_to_send:
        return _LAST_GOOD_DATA if _LAST_GOOD_DATA else []

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
    models_to_try = [model_name]
    if fallback_model and fallback_model != model_name:
        models_to_try.append(fallback_model)

    for current_model in models_to_try:
        for attempt in range(ai_retry + 1):
            try:
                if provider == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    resp = requests.post(
                        url,
                        json={"contents": [{"parts": [{"text": json_prompt}]}]},
                        headers={'Content-Type': 'application/json'},
                        timeout=ai_timeout
                    )
                    if resp.status_code == 200:
                        response_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                        break

                elif provider == "groq":
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    use_model = current_model
                    if use_model == "llama3-8b-8192": use_model = "llama-3.1-8b-instant"
                    resp = requests.post(
                        url,
                        json={
                            "messages": [{"role": "user", "content": json_prompt}],
                            "model": use_model,
                            "response_format": {"type": "json_object"}
                        },
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=ai_timeout
                    )
                    if resp.status_code == 200:
                        response_text = resp.json()['choices'][0]['message']['content']
                        break

                elif provider == "openai":
                    url = base_url if base_url else "https://api.openai.com/v1/chat/completions"
                    if "chat/completions" not in url:
                        url = url.rstrip('/') + "/chat/completions"

                    resp = requests.post(
                        url,
                        json={
                            "messages": [{"role": "user", "content": json_prompt}],
                            "model": current_model,
                            "response_format": {"type": "json_object"}
                        },
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        timeout=ai_timeout
                    )
                    if resp.status_code == 200:
                        response_text = resp.json()['choices'][0]['message']['content']
                        break
                    else:
                        _LOGGER.warning(f"OpenAI Error {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                _LOGGER.warning(f"AI timeout (attempt {attempt + 1}/{ai_retry + 1}) với model {current_model}")
            except Exception as e:
                _LOGGER.warning(f"AI error (attempt {attempt + 1}/{ai_retry + 1}): {e}")

        if response_text:
            break  # Thành công, thoát khỏi vòng lặp model
        elif current_model != models_to_try[-1]:
            _LOGGER.info(f"Chuyển sang fallback model: {fallback_model}")

    # Nếu không có response, trả về cache
    if not response_text:
        _LOGGER.error("Không thể lấy dữ liệu từ AI, sử dụng cache")
        return _LAST_GOOD_DATA if _LAST_GOOD_DATA else []

    # 3. GHÉP DỮ LIỆU AI VÀO DỮ LIỆU GỐC (ẢNH, LINK)
    try:
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

        # Lưu cache
        _LAST_GOOD_DATA = final_result
        return final_result

    except Exception as e:
        _LOGGER.error(f"Lỗi parse AI JSON: {e}")
        return _LAST_GOOD_DATA if _LAST_GOOD_DATA else []