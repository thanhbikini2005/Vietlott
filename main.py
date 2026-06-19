"""
main.py — Entry point cho GitHub Actions
Quyết định gửi PICKS hay RESULTS dựa theo giờ chạy
"""
import os, json
from datetime import datetime
from analysis import analyze_game, load_data
from telegram_sender import (
    send_telegram, build_daily_picks_message,
    build_result_message, load_scores, save_scores
)

DATA_FILE = "data/history.json"
PICKS_FILE = "data/today_picks.json"

def get_mode():
    """Xác định chế độ theo giờ UTC"""
    hour = datetime.utcnow().hour
    if hour == 0:   return "picks"      # 7:00 SA VN
    if hour == 4:   return "results_morning"   # 11:30 SA — Lotto sáng
    if hour == 11:  return "results_evening"   # 18:30 — Mega/Max3D+
    if hour == 14:  return "results_night"     # 21:30 — Lotto tối
    return os.environ.get("MODE", "picks")

def load_picks():
    if os.path.exists(PICKS_FILE):
        with open(PICKS_FILE) as f:
            return json.load(f)
    return {}

def save_picks(picks):
    os.makedirs("data", exist_ok=True)
    with open(PICKS_FILE, "w") as f:
        json.dump(picks, f, indent=2)

def run_picks():
    """Gửi bộ số dự đoán buổi sáng"""
    if not os.path.exists(DATA_FILE):
        # Fallback: tạo data từ seed
        import subprocess
        subprocess.run(["python", "data/seed_data.py"])

    data = load_data()
    analyses = {}
    picks_today = {}

    for gkey in ["mega645", "power655", "max3d_plus", "lotto535"]:
        a = analyze_game(gkey, data)
        analyses[gkey] = a
        if a:
            picks_today[gkey] = {
                "user": a["user_pick"],
                "ai": a["ai_pick"],
            }

    save_picks(picks_today)
    msg = build_daily_picks_message(analyses)
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if token and chat_id and token != "YOUR_BOT_TOKEN":
        send_telegram(msg, token, chat_id)
    else:
        print("⚠️  Chưa set TELEGRAM_TOKEN / TELEGRAM_CHAT_ID")
        print("   Tin nhắn sẽ gửi:\n")
        print(msg)

def run_results(games_to_check):
    """Kiểm tra kết quả và gửi báo cáo"""
    data = load_data()
    picks = load_picks()
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    for gkey in games_to_check:
        if gkey not in picks:
            continue
        records = data.get(gkey, [])
        if not records:
            continue
        latest = records[-1]  # Kết quả mới nhất đã scrape
        analysis = analyze_game(gkey, data)
        if not analysis:
            continue

        user_pick = picks[gkey]["user"]
        ai_pick = picks[gkey]["ai"]

        msg = build_result_message(gkey, analysis, latest, user_pick, ai_pick)

        if token and chat_id and token != "YOUR_BOT_TOKEN":
            send_telegram(msg, token, chat_id)
        else:
            print(msg)
            print()

if __name__ == "__main__":
    mode = get_mode()
    print(f"🚀 Mode: {mode} | UTC: {datetime.utcnow().strftime('%H:%M')}")

    if mode == "picks":
        run_picks()
    elif mode == "results_morning":
        run_results(["lotto535"])  # Lotto 5/35 kỳ sáng
    elif mode == "results_evening":
        run_results(["mega645", "max3d_plus", "power655"])  # 18:00
    elif mode == "results_night":
        run_results(["lotto535"])  # Lotto 5/35 kỳ tối

    print("\n✅ Done!")
