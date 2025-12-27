import requests
import feedparser
import re
import json
import logging

# Setup basic logging to see errors if any
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# --- CẤU HÌNH TEST ---
API_KEY = "local-proxy-key"
BASE_URL = "https://proxy.naai.studio/v1" # Thử thêm /v1
PROVIDER = "openai"
SOURCES = ["https://vnexpress.net/rss/tin-moi-nhat.rss"]
USER_STYLE = "Văn phong biên tập viên tin tức, nghiêm túc, dễ hiểu."
MODEL_NAME = "gpt-3.5-turbo" # Model giả định, proxy của bạn có thể map sang model khác
SUMMARY_LEN = "Tiêu chuẩn (Khoảng 150 từ)"

# --- COPY CORE LOGIC TỪ sensor.py (đã lược bỏ phần phụ thuộc HA) ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}
BAD_KEYWORDS = ["tử vong", "chết", "tai nạn", "giết", "hiếp", "thảm sát", "bắt giữ", "ma túy", "mại dâm"]

def fetch_and_process_json_test(api_key, provider, sources, user_style, model_name, summary_len, base_url):
    print(f"🔄 Đang tải tin tức từ: {sources[0]}...")

    length_instruction = "khoảng 150 từ"
    if "Ngắn" in summary_len: length_instruction = "ngắn gọn, khoảng 80 từ"
    elif "Chi tiết" in summary_len: length_instruction = "chi tiết, khoảng 300 từ"

    articles_to_send = []

    # 1. TẢI RSS VÀ LỌC TIN
    for url in sources:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                t = entry.get('title', '').strip()
                link = entry.get('link', '')
                desc = entry.get('description', '')

                if any(bad in t.lower() for bad in BAD_KEYWORDS):
                    continue

                img_url = None
                img_match = re.search(r'src="([^"]+jpg|[^"]+png|[^"]+jpeg)"', desc)
                if img_match:
                    img_url = img_match.group(1)

                # Lấy ít tin thôi để test cho nhanh (3 tin)
                if len(articles_to_send) < 3:
                    articles_to_send.append({
                        "original_title": t,
                        "link": link,
                        "image": img_url
                    })
        except Exception as e:
            print(f"Lỗi tải RSS: {e}")

    if not articles_to_send:
        print("❌ Không tìm thấy bài báo nào phù hợp.")
        return []

    print(f"✅ Đã tìm thấy {len(articles_to_send)} bài báo. Đang gửi sang AI Proxy...")
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
        if provider == "openai":
            url = base_url if base_url else "https://api.openai.com/v1/chat/completions"
            if "chat/completions" not in url:
                url = url.rstrip('/') + "/chat/completions"

            print(f"📡 Calling POST: {url}")

            resp = requests.post(
                url,
                json={
                    "messages": [{"role": "user", "content": json_prompt}],
                    "model": model_name,
                    "response_format": {"type": "json_object"}
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=40
            )

            print(f"Status Code: {resp.status_code}")

            if resp.status_code == 200:
                response_text = resp.json()['choices'][0]['message']['content']
                print("✅ AI đã phản hồi dữ liệu.")
            else:
                 print(f"❌ OpenAI Error {resp.status_code}: {resp.text}")
                 return []

        # 3. PARSE
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

        final_result = []
        for i, article in enumerate(articles_to_send):
            summary = "Không có tóm tắt"
            if i < len(ai_data):
                summary = ai_data[i].get('summary', '')

            final_result.append({
                "title": article['original_title'],
                "summary": summary
            })

        return final_result

    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")

    return []

# --- CHẠY TEST ---
if __name__ == "__main__":
    results = fetch_and_process_json_test(API_KEY, PROVIDER, SOURCES, USER_STYLE, MODEL_NAME, SUMMARY_LEN, BASE_URL)

    print("\n" + "="*50)
    print("KẾT QUẢ TÓM TẮT")
    print("="*50)
    for res in results:
        print(f"📰 {res['title']}")
        print(f"📝 {res['summary']}")
        print("-" * 30)
