"""
main.py — Chạy mỗi 10 phút trong GitHub Actions
Phát hiện kết quả mới → gửi Telegram ngay lập tức
"""
import os, json
from datetime import datetime
from analysis import analyze_game, load_data, BASE_DIR
from scraper_live import scrape_and_detect_new, mark_as_sent
from telegram_sender import (
    send_telegram, build_daily_picks_message,
    build_result_message, load_scores
)

PICKS_FILE = os.path.join(BASE_DIR, "data", "today_picks.json")

def load_picks():
    if os.path.exists(PICKS_FILE):
        with open(PICKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_picks(picks):
    os.makedirs(os.path.dirname(PICKS_FILE), exist_ok=True)
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)

def is_morning(hour_vn):
    """7:00 SA gửi picks"""
    return hour_vn == 7

def run_picks(data):
    """Gửi dự đoán buổi sáng"""
    analyses    = {}
    picks_today = {}

    for gkey in ["mega645", "power655", "max3d_plus", "lotto535"]:
        a = analyze_game(gkey, data)
        analyses[gkey] = a
        if a:
            picks_today[gkey] = {
                "user": a["user_pick"],
                "ai":   a["ai_pick"],
            }

    save_picks(picks_today)
    msg = build_daily_picks_message(analyses)
    return msg

def run_results(new_results, data):
    """Gửi kết quả ngay khi phát hiện có kết quả mới"""
    picks   = load_picks()
    messages = []

    for gkey, actual_result in new_results.items():
        if gkey not in picks:
            print(f"  ⚠️  Không có picks cho {gkey} hôm nay — bỏ qua")
            mark_as_sent(gkey, actual_result)
            continue

        analysis = analyze_game(gkey, data)
        if not analysis:
            continue

        msg = build_result_message(
            gkey, analysis, actual_result,
            picks[gkey]["user"],
            picks[gkey]["ai"]
        )
        messages.append((gkey, actual_result, msg))

    return messages

def main():
    now_vn   = datetime.utcnow().hour + 7  # UTC+7
    if now_vn >= 24: now_vn -= 24
    now_str  = datetime.now().strftime("%H:%M %d/%m/%Y")
    token    = os.environ.get("TELEGRAM_TOKEN")
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID")

    print(f"🚀 Chạy lúc {now_str} (VN giờ {now_vn}:xx)")

    # ── Bước 1: Scrape và phát hiện kết quả mới ──
    print("\n🔄 Kiểm tra kết quả mới...")
    new_results, data = scrape_and_detect_new()

    # ── Bước 2: Gửi picks buổi sáng (7:00-7:09 VN) ──
    if is_morning(now_vn):
        print("\n📤 Gửi dự đoán buổi sáng...")
        msg = run_picks(data)
        if token and chat_id:
            send_telegram(msg, token, chat_id)
        else:
            print(msg)

    # ── Bước 3: Gửi kết quả mới (bất kỳ giờ nào) ──
    if new_results:
        print(f"\n🔔 Phát hiện {len(new_results)} kết quả mới!")
        messages = run_results(new_results, data)
        for gkey, actual_result, msg in messages:
            if token and chat_id:
                send_telegram(msg, token, chat_id)
            else:
                print(msg)
            mark_as_sent(gkey, actual_result)
            print(f"  ✅ Đã gửi + đánh dấu: {gkey}")
    else:
        print("  ⏳ Chưa có kết quả mới — chờ lần sau")

    print("\n✅ Done!")

if __name__ == "__main__":
    main()
