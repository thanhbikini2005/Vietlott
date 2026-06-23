"""
main.py — Gửi picks lúc 7h sáng, gửi kết quả khi có KQ mới
Fix: nếu không có picks thì tự tạo picks trước khi gửi kết quả
"""
import os, json
from datetime import datetime
from analysis import analyze_game, load_data, BASE_DIR
from scraper_live import scrape_and_detect_new, mark_as_sent
from telegram_sender import (
    send_telegram, build_daily_picks_message,
    build_result_message,
)

PICKS_FILE = os.path.join(BASE_DIR, "data", "today_picks.json")
PICKS_DATE_FILE = os.path.join(BASE_DIR, "data", "picks_date.txt")

def load_picks():
    if os.path.exists(PICKS_FILE):
        with open(PICKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_picks(picks):
    os.makedirs(os.path.dirname(PICKS_FILE), exist_ok=True)
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)
    # Lưu ngày tạo picks
    with open(PICKS_DATE_FILE, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))

def picks_are_today():
    """Kiểm tra picks đã được tạo hôm nay chưa"""
    if not os.path.exists(PICKS_DATE_FILE):
        return False
    with open(PICKS_DATE_FILE) as f:
        return f.read().strip() == datetime.now().strftime("%Y-%m-%d")

def make_picks(data):
    """Tạo picks cho hôm nay"""
    analyses    = {}
    picks_today = {}
    for gkey in ["mega645", "power655", "max3d_plus", "lotto535"]:
        a = analyze_game(gkey, data)
        analyses[gkey] = a
        if a:
            picks_today[gkey] = {"user": a["user_pick"], "ai": a["ai_pick"]}
    save_picks(picks_today)
    return analyses, picks_today

def is_morning():
    """7:00-7:59 VN = 0:00-0:59 UTC"""
    hour_utc = datetime.utcnow().hour
    return hour_utc == 0

def main():
    now_vn  = (datetime.utcnow().hour + 7) % 24
    today   = datetime.now().strftime("%Y-%m-%d")
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    print(f"🚀 {datetime.now().strftime('%H:%M %d/%m/%Y')} (VN {now_vn}h)")

    # ── Scrape kết quả mới ──
    print("\n🔄 Kiểm tra kết quả mới...")
    new_results, data = scrape_and_detect_new()

    # ── Gửi picks buổi sáng HOẶC nếu chưa có picks hôm nay ──
    if is_morning() or not picks_are_today():
        reason = "7h sáng" if is_morning() else "chưa có picks hôm nay"
        print(f"\n📤 Tạo và gửi picks ({reason})...")
        analyses, picks_today = make_picks(data)
        msg = build_daily_picks_message(analyses)
        if token and chat_id:
            send_telegram(msg, token, chat_id)
        else:
            print(msg)

    # ── Gửi kết quả mới ──
    if new_results:
        print(f"\n🔔 {len(new_results)} kết quả mới!")
        picks = load_picks()

        # Nếu vẫn không có picks → tạo ngay
        if not picks:
            print("  ⚠️ Không có picks, tạo ngay...")
            _, picks = make_picks(data)

        for gkey, actual_result in new_results.items():
            analysis = analyze_game(gkey, data)
            if not analysis:
                mark_as_sent(gkey, actual_result)
                continue

            if gkey not in picks:
                print(f"  ⚠️ Không có picks cho {gkey}, bỏ qua phần so sánh")
                mark_as_sent(gkey, actual_result)
                continue

            msg = build_result_message(
                gkey, analysis, actual_result,
                picks[gkey]["user"],
                picks[gkey]["ai"]
            )
            if token and chat_id:
                send_telegram(msg, token, chat_id)
            else:
                print(msg)
            mark_as_sent(gkey, actual_result)
            print(f"  ✅ Đã gửi: {gkey}")
    else:
        print("⏳ Không có kết quả mới")

    print("\n✅ Done!")

if __name__ == "__main__":
    main()
