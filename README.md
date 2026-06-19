# 🎯 Vietlott Daily Bot

Bot tự động phân tích & gửi dự đoán Vietlott về Telegram hàng ngày.

## Chơi gì
- 🔵 **Mega 6/45** — Thứ 4, 6, Chủ nhật 18:00
- 🟡 **Power 6/55** — Thứ 3, 5, 7 18:00  
- 🟢 **Max 3D+** — Thứ 3, 4, 5, 6, 7, CN 18:00
- 🔴 **Lotto 5/35** — Hàng ngày 13:00 & 21:00

## Cách hoạt động
Bot gửi **2 bộ số** mỗi ngày cho mỗi giải:
- 🧠 **[BẠN]** — Dựa trên thống kê tần suất tuần/tháng/quý/năm + vị trí (đầu/giữa/cuối)
- 🤖 **[AI]** — Dựa trên số "nguội" (lâu chưa ra) + phân phối đều theo vùng số

Sau mỗi kỳ quay, bot gửi kết quả và cập nhật **bảng đua BẠN vs AI**.

## Setup (5 phút)

### 1. Tạo Telegram Bot
1. Nhắn `@BotFather` trên Telegram → `/newbot`
2. Lấy **Bot Token** (dạng `123456789:AABBcc...`)
3. Chat với bot của bạn 1 tin → lấy **Chat ID** từ:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 2. Fork repo này lên GitHub

### 3. Thêm Secrets
Vào repo → Settings → Secrets and variables → Actions:
- `TELEGRAM_TOKEN` = token bot của bạn
- `TELEGRAM_CHAT_ID` = chat ID của bạn

### 4. Bật GitHub Actions
Vào tab **Actions** → bật workflow → **Run workflow** để test ngay

## Lịch gửi tin (giờ Việt Nam)
| Giờ VN | Nội dung |
|--------|----------|
| 07:00 sáng | 🎯 Dự đoán số cho ngày hôm đó |
| 11:30 trưa | ✅ Kết quả Lotto 5/35 kỳ sáng |
| 18:30 tối  | ✅ Kết quả Mega/Power/Max3D+ |
| 21:30 tối  | ✅ Kết quả Lotto 5/35 kỳ tối |

## Cấu trúc files
```
vietlott-bot/
├── .github/workflows/daily.yml  # Lịch chạy tự động
├── main.py                       # Entry point
├── scraper_live.py               # Thu thập dữ liệu thật
├── analysis.py                   # Phân tích & chọn số
├── telegram_sender.py            # Gửi tin nhắn
└── data/
    ├── history.json              # Lịch sử kết quả
    ├── today_picks.json          # Số đã chọn hôm nay
    └── scores.json               # Bảng đua BẠN vs AI
```

## Ghi chú quan trọng
> Đây là bot theo dõi & giải trí. Không có hệ thống nào đảm bảo trúng xổ số.
> Chơi có trách nhiệm, chỉ bỏ số tiền bạn chấp nhận mất được.
