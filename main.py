"""
main.py — Entry point cho GitHub Actions
"""
import os, json
from datetime import datetime
from analysis import analyze_game, load_data, BASE_DIR
from telegram_sender import (
    send_telegram, build_daily_picks_message,
    build_result_message, load_scores, save_scores
)

PICKS_FILE = os.path.join(BASE_DIR, "data", "today_picks.json")

def get_mode():
    hour = datetime.utcnow().hour
    if hour == 0:  return "picks"
    if hour == 4:  return "results_morning"
    if hour == 11: return "results_evening"
    if hour == 14: return "results_night"
    return os.environ.get("MODE", "picks")

def load_picks():
    if os.path.exists(PICKS_FILE):
        with open(PICKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_picks(picks):
    os.makedirs(os.path.dirname(PICKS_FILE), exist_ok=True)
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2)

def run_picks():
    data      = load_data()
    analyses  = {}
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
    msg     = build_daily_picks_message(analyses)
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if token and chat_id and token != "YOUR_BOT_TOKEN":
        send_telegram(msg, token, chat_id)
    else:
        print("⚠️  Chưa set TELEGRAM_TOKEN / TELEGRAM_CHAT_ID")
        print(msg)

def run_results(games_to_check):
    data    = load_data()
    picks   = load_picks()
    token   = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    for gkey in games_to_check:
        if gkey not in picks:
            print(f"  ⚠️  Không có picks cho {gkey} hôm nay")
            continue
        records = data.get(gkey, [])
        if not records:
            continue
        latest   = records[-1]
        analysis = analyze_game(gkey, data)
        if not analysis:
            continue

        msg = build_result_message(
            gkey, analysis, latest,
            picks[gkey]["user"],
            picks[gkey]["ai"]
        )

        if token and chat_id and token != "YOUR_BOT_TOKEN":
            send_telegram(msg, token, chat_id)
        else:
            print(msg)

if __name__ == "__main__":
    mode = get_mode()
    print(f"🚀 Mode: {mode} | UTC: {datetime.utcnow().strftime('%H:%M')}")

    if mode == "picks":
        run_picks()
    elif mode == "results_morning":
        run_results(["lotto535"])
    elif mode == "results_evening":
        run_results(["mega645", "max3d_plus", "power655"])
    elif mode == "results_night":
        run_results(["lotto535"])

    print("\n✅ Done!")
