# 📊 TikTok Channel Statistics Analyzer

Tool phân tích toàn diện thông số kênh TikTok - Thu thập và phân tích dữ liệu từ bất kỳ kênh TikTok nào.

## ✨ Tính năng

### 🎯 Thông tin kênh
- ✅ Tên kênh & Username
- ✅ Bio/Description  
- ✅ Số lượng Followers
- ✅ Số lượng Following
- ✅ Tổng Likes của kênh

### 📈 Thống kê Video
- ✅ Tổng số video
- ✅ Tổng lượt xem (Total Views)
- ✅ Trung bình views/video
- ✅ Top 10 video hot nhất
- ✅ Thông tin chi tiết từng video (views, caption, link)
- ⚠️ Engagement Rate (nếu có đủ dữ liệu)

### 💾 Xuất dữ liệu
- ✅ Lưu báo cáo JSON chi tiết
- ✅ Xuất danh sách video ra CSV
- ✅ Tên file tự động theo kênh và thời gian

## 🚀 Cài đặt

### Bước 1: Cài đặt Python
Đảm bảo bạn đã cài Python 3.8 trở lên.

### Bước 2: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Bước 3: Cài đặt Playwright browsers
```bash
playwright install chromium
```

## 📖 Hướng dẫn sử dụng

### Cách 1: Chạy đơn giản
```bash
python tiktok_counter.py
```
Sau đó nhập URL kênh TikTok khi được yêu cầu.

### Cách 2: Truyền URL trực tiếp
```bash
python tiktok_counter.py https://www.tiktok.com/@username
```

### Cách 3: Lưu kết quả vào file
```bash
# Lưu JSON
python tiktok_counter.py https://www.tiktok.com/@username --save-json

# Lưu CSV
python tiktok_counter.py https://www.tiktok.com/@username --save-csv

# Lưu cả JSON và CSV
python tiktok_counter.py https://www.tiktok.com/@username --save-json --save-csv
```

### Cách 4: Tùy chỉnh số lần scroll
```bash
# Scroll nhiều hơn để load nhiều video hơn (mặc định: 20)
python tiktok_counter.py https://www.tiktok.com/@username --max-scrolls 30
```

### Cách 5: Hiển thị browser (debug mode)
```bash
# Xem browser hoạt động (không chạy ẩn)
python tiktok_counter.py https://www.tiktok.com/@username --headless
```

## 📋 Các tham số dòng lệnh

| Tham số | Mô tả | Mặc định |
|---------|-------|----------|
| `url` | URL kênh TikTok | Yêu cầu nhập |
| `--save-json` | Lưu kết quả vào JSON | Không |
| `--save-csv` | Xuất danh sách video ra CSV | Không |
| `--max-scrolls` | Số lần scroll tối đa | 20 |
| `--headless` | Hiển thị browser | Ẩn browser |

## 📊 Ví dụ Output

```
╔════════════════════════════════════════════════╗
║   TIKTOK CHANNEL STATISTICS ANALYZER           ║
║   Phân tích toàn diện kênh TikTok              ║
║   Version: 2.0.0 - Enhanced Edition            ║
╚════════════════════════════════════════════════╝

======================================================================
📊 BÁO CÁO PHÂN TÍCH KÊNH TIKTOK
======================================================================

🎯 THÔNG TIN KÊNH:
  📱 Tên: Example Channel
  👤 Username: @example
  📝 Bio: Welcome to my channel!
  👥 Followers: 1.50M (1,500,000)
  ➕ Following: 250 (250)
  ❤️ Channel Likes: 45.20M (45,200,000)

📈 THỐNG KÊ VIDEO:
  📹 Tổng số video: 150
  👁️ TỔNG LƯỢT XEM: 125.50M (125,500,000 views)
  📊 Trung bình views/video: 836.67K

🔗 URL: https://www.tiktok.com/@example
🕐 Thời gian scrape: 2025-10-01T10:30:45.123456

📌 TOP 10 VIDEO HOT NHẤT: (từ 150 video có data)
----------------------------------------------------------------------

1. 👁️ 5.20M views (5.2M)
   📝 Amazing video content here...
   🔗 https://www.tiktok.com/@example/video/1234567890
...
```

## 📁 File Output

### JSON Output
File `tiktok_stats_[tên_kênh]_[timestamp].json` chứa:
- Thông tin kênh đầy đủ
- Thống kê tổng hợp
- Danh sách chi tiết tất cả video

### CSV Output  
File `tiktok_videos_[tên_kênh]_[timestamp].csv` chứa:
- Index, Views, Likes, Comments, Shares
- Caption và Link của từng video

## ⚠️ Lưu ý

1. **TikTok có thể block**: Tool sử dụng web scraping nên TikTok có thể phát hiện và block. Nên:
   - Không chạy quá nhiều lần liên tục
   - Sử dụng VPN nếu cần
   - Tăng thời gian chờ giữa các request

2. **Dữ liệu không đầy đủ**: 
   - Likes/Comments/Shares thường không hiển thị ở trang channel
   - Chỉ lấy được số views từ trang channel
   - Để lấy full stats cần vào từng video riêng (tốn thời gian)

3. **Selector có thể thay đổi**: 
   - TikTok thường xuyên thay đổi cấu trúc HTML
   - Tool có thể cần cập nhật selector định kỳ

4. **Hiệu suất**:
   - Mỗi lần scroll mất ~3 giây
   - Load 100 video có thể mất 5-10 phút
   - Tăng `--max-scrolls` sẽ lâu hơn nhưng lấy được nhiều video hơn

## 🔧 Khắc phục sự cố

### Lỗi "Không tìm thấy video"
- Tăng thời gian chờ trong code (line ~100, 111)
- Thử lại với `--headless` để xem browser
- Kiểm tra URL có đúng không

### Lỗi timeout
- Tăng timeout trong code (line 97)
- Kiểm tra kết nối internet
- Thử VPN nếu bị block

### Dữ liệu sai/thiếu
- TikTok có thể đã thay đổi selector
- Cần cập nhật code với selector mới
- Xem HTML source để tìm selector mới

## 📝 TODO - Tính năng tương lai

- [ ] Tự động retry khi bị lỗi
- [ ] Progress bar hiển thị tiến độ
- [ ] Crawl chi tiết từng video (likes, comments, shares)
- [ ] So sánh nhiều kênh
- [ ] Vẽ biểu đồ thống kê
- [ ] Export Excel với formatting
- [ ] API mode để tích hợp vào app khác

## 📄 License

Free to use for personal and educational purposes.

## 🤝 Đóng góp

Mọi đóng góp, báo lỗi, hoặc đề xuất tính năng đều được hoan nghênh!

---
**Made with ❤️ for TikTok Analytics**

