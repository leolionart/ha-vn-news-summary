Dưới đây là file README.md chuyên nghiệp, đầy đủ hướng dẫn cài đặt và sử dụng cho dự án của bạn. Bạn có thể tạo file README.md trong cùng thư mục component hoặc dùng để đăng lên Github chia sẻ cho cộng đồng.

📰 VN News Summary AI for Home Assistant
VN News Summary AI là một Custom Component cho Home Assistant, giúp bạn tự động thu thập tin tức từ các báo điện tử Việt Nam (VnExpress, Tuổi Trẻ, Dân Trí...), sử dụng trí tuệ nhân tạo (Gemini hoặc Groq) để tóm tắt nội dung, và tạo ra các cảm biến (sensor) để đọc trên loa thông minh (Google Home/Alexa).

✨ Tính năng nổi bật
Đa nguồn tin: Hỗ trợ lấy tin từ nhiều nguồn RSS cùng lúc (VnExpress, Tuổi Trẻ, Dân Trí, Thanh Niên...).

Trí tuệ nhân tạo:

Hỗ trợ Google Gemini (Miễn phí, tốc độ cao).

Hỗ trợ Groq (Llama 3, Mixtral...) với khả năng tự động cập nhật danh sách Model mới nhất.

20 Cảm biến tin tức: Tự động tách tin tức thành 20 entity riêng biệt (sensor.vn_news_01 -> 02...), giúp dễ dàng chọn bài để đọc.

Tùy chỉnh linh hoạt:

Lựa chọn độ dài tóm tắt: Ngắn (80 từ), Tiêu chuẩn (150 từ), Chi tiết (300 từ)...

Tùy chỉnh phong cách (Prompt): Hài hước, Nghiêm túc, Châm biếm...

Thông minh: Tự động sửa lỗi link RSS hỏng, tự động bỏ qua tin rác, định dạng đầu ra JSON chuẩn xác.

📂 Cấu trúc thư mục
Đảm bảo bạn đã tạo các file theo cấu trúc sau trong thư mục /config:

Plaintext

/config/custom_components/vn_news_summary/
├── __init__.py
├── config_flow.py
├── const.py
├── manifest.json
├── sensor.py
├── services.yaml
└── icon.png  (Tùy chọn: Icon hiển thị)
🚀 Cài đặt
Tải toàn bộ code và đặt vào thư mục /config/custom_components/vn_news_summary/.

Khởi động lại Home Assistant (Bắt buộc để hệ thống cài đặt thư viện feedparser).

Xóa Cache trình duyệt (Ctrl + F5) để hiển thị icon (nếu có).

⚙️ Cấu hình
Vào Settings > Devices & Services.

Bấm Add Integration > Tìm kiếm "VN News Summary AI".

Điền thông tin:

AI Provider: Chọn Gemini hoặc Groq.

API Key: Nhập key tương ứng.

Model: (Nếu chọn Groq) Chọn model mong muốn (VD: llama-3.1-8b-instant).

Độ dài tóm tắt: Chọn mức độ chi tiết bạn muốn nghe.

Nguồn tin (Sources): Dán link RSS (mỗi dòng 1 link hoặc ngăn cách bằng dấu phẩy).

Gợi ý link chuẩn:

https://vnexpress.net/rss/tin-moi-nhat.rss

https://tuoitre.vn/rss/tin-moi-nhat.rss

https://dantri.com.vn/trangchu.rss

Bấm Submit.

📡 Entities & Attributes
Sau khi cài đặt thành công, hệ thống sẽ tạo ra 20 sensors:

sensor.vn_news_01: Tin mới nhất số 1.

...

sensor.vn_news_20: Tin mới nhất số 20.

Thông tin trong mỗi sensor:

State: Đoạn tóm tắt ngắn (để hiển thị trên Dashboard).

Attribute full_summary: Nội dung tóm tắt đầy đủ (Dùng để gửi cho loa đọc).

Attribute title: Tiêu đề gốc của bài báo.

🔊 Hướng dẫn tạo Automation (Đọc loa)
Cách 1: Đọc liên tục (Sử dụng Smart Wait)
Cách này giúp loa đọc xong tin này mới chuyển sang tin khác, không bị chồng chéo.

YAML

alias: "Đọc điểm tin sáng"
trigger:
  - platform: time
    at: "07:00:00"
action:
  # Cập nhật tin mới nhất
  - service: homeassistant.update_entity
    target:
      entity_id: sensor.vn_news_sensor

  # Đọc tin 1
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home
      message: "Tin số 1: {{ state_attr('sensor.vn_news_01', 'full_summary') }}"
  
  # Chờ loa đọc xong
  - delay: "00:00:02"
  - wait_template: "{{ is_state('media_player.google_home', 'idle') }}"
    timeout: "00:05:00"

  # Đọc tin 2
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home
      message: "Tin số 2: {{ state_attr('sensor.vn_news_02', 'full_summary') }}"
Cách 2: Script đọc theo yêu cầu (Hey Google)
Tạo Script để gọi bằng Google Assistant.

YAML

alias: Read News
sequence:
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home
      message: >
        Chào bạn, đây là 3 tin nóng nhất:
        {{ state_attr('sensor.vn_news_01', 'full_summary') }}
        Tiếp theo,
        {{ state_attr('sensor.vn_news_02', 'full_summary') }}
        Và cuối cùng,
        {{ state_attr('sensor.vn_news_03', 'full_summary') }}
❓ Khắc phục sự cố thường gặp
1. Sensor báo "Lỗi: Không lấy được tin tức nào"

Kiểm tra lại kết nối mạng của Home Assistant (có chặn Google/Groq không?).

Kiểm tra link RSS. Đảm bảo dùng link .rss, không dùng link trang web .html.

2. Groq báo lỗi "Model decommissioned"

Groq thường xuyên thay đổi model. Hãy vào Configure của Integration, menu chọn Model sẽ tự động tải danh sách mới nhất về. Hãy chọn model khác.

3. Không thấy Icon hình tờ báo

Hãy mở Home Assistant bằng Tab ẩn danh (Incognito). Nếu thấy icon hiện, hãy xóa Cache trình duyệt của bạn.
