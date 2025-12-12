Dưới đây là nội dung file **`README.md`** chuyên nghiệp, đầy đủ và chi tiết nhất cho phiên bản "Ultimate" (tích hợp Podcast, Ảnh thumbnail, Lọc tin rác) mà chúng ta vừa xây dựng.

Bạn có thể copy nội dung này, tạo file tên là `README.md` trong thư mục dự án và upload lên GitHub.

-----

# 📰 VN News Summary AI (Home Assistant Integration)

[](https://github.com/hacs/integration)
[](https://www.home-assistant.io/)
[](https://github.com/)

**VN News Summary AI** là một thành phần tùy chỉnh (Custom Component) mạnh mẽ dành cho Home Assistant. Nó tự động thu thập tin tức từ các báo điện tử Việt Nam (VnExpress, Tuổi Trẻ, Dân Trí...), sử dụng trí tuệ nhân tạo (Google Gemini hoặc Groq) để tóm tắt nội dung, lọc tin tiêu cực và chuẩn bị sẵn kịch bản để đọc trên loa thông minh.

*(Hình ảnh minh họa hiển thị trên Dashboard)*

## ✨ Tính năng nổi bật

  * **🤖 Đa nền tảng AI:** Hỗ trợ **Google Gemini** (Miễn phí, tốc độ cao) và **Groq** (Llama 3, Mixtral - tự động cập nhật danh sách model).
  * **📸 Hiển thị ảnh bìa (Thumbnail):** Tự động trích xuất hình ảnh từ bài báo để hiển thị đẹp mắt trên Dashboard.
  * **🎙️ Chế độ Podcast:** Tự động gộp nội dung tóm tắt của 20 tin thành một bài phát thanh liền mạch với lời dẫn nhập/kết thúc (chỉ cần gọi 1 lệnh TTS là đọc hết).
  * **🛡️ Bộ lọc tin tiêu cực:** Tự động loại bỏ các tin tức chứa từ khóa nhạy cảm (tai nạn, giết người,...) để bản tin buổi sáng trong lành hơn.
  * **🧩 20 Sensors riêng biệt:** Tách tin tức thành 20 thực thể riêng biệt (`sensor.vn_news_01` -\> `20`) để bạn tùy ý xử lý.
  * **📝 Tùy chỉnh linh hoạt:**
      * Chọn độ dài tóm tắt: Ngắn (80 từ), Tiêu chuẩn (150 từ), Chi tiết (300 từ)...
      * Tùy chỉnh giọng văn (Prompt): Hài hước, nghiêm túc, châm biếm...

## 📂 Cài đặt

### Cách 1: Qua HACS (Khuyên dùng)

1.  Đảm bảo bạn đã cài đặt [HACS](https://hacs.xyz/).
2.  Vào HACS \> Integrations \> Bấm menu 3 chấm góc trên bên phải \> **Custom repositories**.
3.  Dán đường dẫn GitHub của repo này vào ô Repository.
4.  Chọn Category: **Integration**.
5.  Bấm **Add**, sau đó tìm kiếm "VN News Summary AI" và cài đặt.
6.  Khởi động lại Home Assistant.

### Cách 2: Cài thủ công

1.  Tải file `.zip` của dự án này về.
2.  Giải nén và copy thư mục `vn_news_summary` vào đường dẫn `/config/custom_components/` trên Home Assistant của bạn.
3.  Cấu trúc thư mục chuẩn sẽ là:
    ```text
    /config/custom_components/vn_news_summary/
    ├── __init__.py
    ├── manifest.json
    ├── sensor.py
    ├── ...
    ```
4.  Khởi động lại Home Assistant.

## ⚙️ Cấu hình

1.  Truy cập **Settings** \> **Devices & Services**.
2.  Bấm nút **+ Add Integration**.
3.  Tìm kiếm **"VN News Summary AI"**.
4.  Điền các thông tin:
      * **AI Provider:** Chọn `gemini` hoặc `groq`.
      * **API Key:** Nhập khóa API của bạn.
      * **Model:** Chọn model AI (Nếu dùng Groq, danh sách sẽ tự tải về).
      * **Độ dài tóm tắt:** Chọn mức độ chi tiết mong muốn.
      * **Nguồn tin (Sources):** Nhập danh sách link RSS (mỗi dòng 1 link hoặc cách nhau bằng dấu phẩy).
          * *VnExpress:* `https://vnexpress.net/rss/tin-moi-nhat.rss`
          * *Tuổi Trẻ:* `https://tuoitre.vn/rss/tin-moi-nhat.rss`
          * *Dân Trí:* `https://dantri.com.vn/trangchu.rss`
5.  Bấm **Submit**.

## 📱 Sử dụng trên Dashboard

Để hiển thị danh sách tin tức kèm hình ảnh đẹp mắt, bạn có thể sử dụng thẻ **Grid** hoặc **Tile** card.

Ví dụ cấu hình YAML cho Dashboard:

```yaml
type: grid
square: false
columns: 2
cards:
  - type: tile
    entity: sensor.vn_news_01
    name: Tin nóng 1
    show_entity_picture: true
  - type: tile
    entity: sensor.vn_news_02
    name: Tin nóng 2
    show_entity_picture: true
  - type: tile
    entity: sensor.vn_news_03
    name: Tin nóng 3
    show_entity_picture: true
  - type: tile
    entity: sensor.vn_news_04
    name: Tin nóng 4
    show_entity_picture: true
```

## 🔊 Automation đọc tin (TTS)

### Kịch bản 1: Chế độ Podcast (Đọc một lèo hết tin)

Đây là cách đơn giản và hay nhất. Sử dụng sensor `sensor.vn_news_podcast`.

```yaml
alias: "Chào buổi sáng - Đọc báo Podcast"
trigger:
  - platform: time
    at: "07:00:00"
action:
  # Cập nhật tin mới nhất
  - service: homeassistant.update_entity
    target:
      entity_id: sensor.vn_news_sensor

  # Đọc nội dung Podcast đã được gộp sẵn
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home_mini
      message: "{{ state_attr('sensor.vn_news_podcast', 'podcast_content') }}"
```

### Kịch bản 2: Hỏi Google để đọc từng tin

Nếu bạn muốn ra lệnh *"Hey Google, read news"* để đọc 3 tin đầu tiên.

```yaml
alias: Read News Script
sequence:
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home
      message: >
        Chào bạn, dưới đây là 3 tin đáng chú ý nhất.
        Tin thứ nhất: {{ state_attr('sensor.vn_news_01', 'full_summary') }}
        Tin thứ hai: {{ state_attr('sensor.vn_news_02', 'full_summary') }}
        Và tin thứ ba: {{ state_attr('sensor.vn_news_03', 'full_summary') }}
```

## ❓ Các vấn đề thường gặp

**1. Sensor hiện "Trống" hoặc "Lỗi"**

  * Kiểm tra lại kết nối mạng của Home Assistant.
  * Kiểm tra API Key có còn hạn mức sử dụng (Quota) không.
  * Kiểm tra Link RSS có đúng định dạng không (phải là `.rss`).

**2. Không thấy hình ảnh bài báo**

  * Không phải nguồn RSS nào cũng cung cấp ảnh trong thẻ `description`. VnExpress và Tuổi Trẻ thường hỗ trợ tốt nhất.
  * Nếu dùng Tile Card, hãy chắc chắn đã bật `show_entity_picture: true`.

**3. Lỗi "Model not found" khi dùng Groq**

  * Groq thường xuyên thay đổi tên Model. Hãy vào **Configure** của Integration, menu chọn Model sẽ tự động tải danh sách mới nhất về.



