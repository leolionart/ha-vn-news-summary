# Quy trình Phát hành Phiên bản mới cho HACS (Release Workflow)

Để Home Assistant (HACS) nhận diện bản cập nhật mới, bạn cần thực hiện đúng quy trình chuẩn hóa dưới đây. Quy trình này đảm bảo phiên bản trong `manifest.json` khớp với GitHub Release Tag.

## 1. Kiểm tra và Cập nhật Version

Trước khi đẩy code, hãy đảm bảo bạn đã tăng số phiên bản.

**File:** `custom_components/vn_news_summary/manifest.json`

```json
{
  ...
  "version": "2.4.1"  <-- Tăng số này lên (ví dụ từ 2.4.0 -> 2.4.1)
  ...
}
```

## 2. Commit và Push Code

Thực hiện commit các thay đổi (bao gồm cả việc đổi version ở trên).

```bash
git add .
git commit -m "Update version to v2.4.1 - [Mô tả ngắn gọn thay đổi]"
git push origin main
```

## 3. Tạo GitHub Release (Bắt buộc cho HACS)

HACS chỉ thông báo cập nhật khi có **GitHub Release** mới trùng khớp với version trong manifest.

**Sử dụng GitHub CLI (Khuyên dùng):**

```bash
# Tạo release với title và ghi chú tự động
gh release create v2.4.1 --title "v2.4.1" --generate-notes
```

**Hoặc làm thủ công trên Web:**
1. Vào [Releases > Draft a new release](https://github.com/leolionart/ha-vn-news-summary/releases/new)
2. **Choose a tag**: Nhập đúng số version (ví dụ: `v2.4.1`).
3. **Release title**: `v2.4.1` (hoặc tên mô tả).
4. Nhấn **Publish release**.

---

## 🤖 Claude Code Automation (Dành cho AI)

Nếu bạn yêu cầu Claude thực hiện quy trình "release", Claude sẽ thực hiện các bước sau:

1.  **Đọc phiên bản hiện tại** trong `custom_components/vn_news_summary/manifest.json`.
2.  **Hỏi người dùng** phiên bản mới muốn đặt (Major/Minor/Patch).
3.  **Tự động sửa file** `manifest.json`.
4.  **Git Commit & Push** thay đổi lên main.
5.  **Tạo GitHub Release** bằng lệnh `gh release create`.

**Câu lệnh kích hoạt:** "Thực hiện release phiên bản mới" hoặc "Publish bản cập nhật HACS".
