"""
telegram_sender.py — Gửi tin nhắn Telegram + tracking win/loss
"""
import json, os, requests
from datetime import datetime
from analysis import analyze_game, load_data

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
SCORE_FILE = "/home/claude/vietlott-bot/data/scores.json"

# ─────────────────────────────────────────────
# TRACKING WIN/LOSS
# ─────────────────────────────────────────────
def load_scores():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE) as f:
            return json.load(f)
    return {
        "user": {"wins": 0, "losses": 0, "points": 0, "history": []},
        "ai":   {"wins": 0, "losses": 0, "points": 0, "history": []},
    }

def save_scores(scores):
    with open(SCORE_FILE, "w") as f:
        json.dump(scores, f, indent=2)

def check_match(pick, result, game_key):
    """Kiểm tra số bộ số trùng"""
    if game_key == "max3d_plus":
        match1 = pick["bo1"] == result.get("bo1", [])
        match2 = pick["bo2"] == result.get("bo2", [])
        return 2 if (match1 and match2) else (1 if (match1 or match2) else 0)
    else:
        matched = len(set(pick) & set(result.get("numbers", [])))
        return matched

# ─────────────────────────────────────────────
# ĐỊNH DẠNG TIN NHẮN
# ─────────────────────────────────────────────
GAME_EMOJI = {
    "mega645": "🔵",
    "power655": "🟡",
    "max3d_plus": "🟢",
    "lotto535": "🔴",
}

def format_pick(pick, game_key):
    if game_key == "max3d_plus":
        return f"Bộ1: {pick['bo1'][0]}-{pick['bo1'][1]}-{pick['bo1'][2]}  |  Bộ2: {pick['bo2'][0]}-{pick['bo2'][1]}-{pick['bo2'][2]}"
    nums = pick.get("numbers", pick) if isinstance(pick, dict) else pick
    return " - ".join(f"{int(n):02d}" for n in sorted(nums))

def build_daily_picks_message(analyses):
    now = datetime.now()
    days_vn = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    day_str = days_vn[now.weekday()]
    date_str = now.strftime("%d/%m/%Y")

    scores = load_scores()
    u = scores["user"]
    a = scores["ai"]
    
    # Ai đang dẫn?
    if u["points"] > a["points"]:
        lead = f"🧠 BẠN đang dẫn +{u['points']-a['points']} điểm"
    elif a["points"] > u["points"]:
        lead = f"🤖 AI đang dẫn +{a['points']-u['points']} điểm"
    else:
        lead = "🤝 Hoà!"

    lines = [
        f"🎯 *VIETLOTT DAILY PICKS — {day_str} {date_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for gkey, analysis in analyses.items():
        if not analysis:
            continue
        emoji = GAME_EMOJI.get(gkey, "⚪")
        name = analysis["name"]
        up = format_pick(analysis["user_pick"], gkey)
        ap = format_pick(analysis["ai_pick"], gkey)

        # Lý do chọn
        top_month = analysis["freq_top10_month"][:3]
        top_str = ", ".join(f"{n}({c}lần)" for n, c in top_month) if top_month else "—"
        pos_dau = analysis["position"]["month"].get("dau", [])
        pos_cuoi = analysis["position"]["month"].get("cuoi", [])
        dau_str = pos_dau[0][0] if pos_dau else "?"
        cuoi_str = pos_cuoi[0][0] if pos_cuoi else "?"

        lines += [
            f"\n{emoji} *{name}*",
            f"┌─────────────────────────────",
            f"│ 🧠 [BẠN - Thống kê]",
            f"│ `{up}`",
            f"│ 📊 Tháng này hay ra: {top_str}",
            f"│ Đầu:{dau_str} | Cuối:{cuoi_str}",
            f"├─────────────────────────────",
            f"│ 🤖 [AI - Số nguội]",
            f"│ `{ap}`",
            f"│ 💭 Chọn số lâu chưa xuất hiện",
            f"└─────────────────────────────",
        ]

    lines += [
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 *BẢNG ĐUA TÍCH LŨY*",
        f"```",
        f"         Trúng  Hụt   Điểm",
        f"🧠 BẠN   {u['wins']:>4}   {u['losses']:>4}   {u['points']:>4}",
        f"🤖 AI    {a['wins']:>4}   {a['losses']:>4}   {a['points']:>4}",
        f"```",
        f"{lead}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)

def build_result_message(game_key, analysis, actual_result, user_pick, ai_pick):
    emoji = GAME_EMOJI.get(game_key, "⚪")
    name = analysis["name"]
    now = datetime.now()

    user_match = check_match(user_pick, actual_result, game_key)
    ai_match = check_match(ai_pick, actual_result, game_key)

    def match_label(m, game_key):
        if game_key == "max3d_plus":
            if m == 2: return "🎉 Trúng cả 2 bộ!"
            if m == 1: return "✅ Trúng 1 bộ"
            return "❌ Không trúng"
        n_pick = 6 if game_key in ["mega645","power655"] else 5
        if m == n_pick: return "🏆 JACKPOT!"
        if m >= 4: return f"🎉 Trúng {m}/{n_pick} — Giải!"
        if m >= 3: return f"✅ Trúng {m}/{n_pick}"
        return f"❌ Trúng {m}/{n_pick}"

    # Cập nhật điểm
    scores = load_scores()
    if game_key != "max3d_plus":
        n_req = 6 if game_key in ["mega645","power655"] else 5
        if user_match >= 3:
            scores["user"]["wins"] += 1
            scores["user"]["points"] += user_match
        else:
            scores["user"]["losses"] += 1
        if ai_match >= 3:
            scores["ai"]["wins"] += 1
            scores["ai"]["points"] += ai_match
        else:
            scores["ai"]["losses"] += 1
    save_scores(scores)

    result_str = format_pick(actual_result, game_key)
    user_str = format_pick(user_pick, game_key)
    ai_str = format_pick(ai_pick, game_key)

    return "\n".join([
        f"✅ *KẾT QUẢ {emoji} {name}* — {now.strftime('%d/%m %H:%M')}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎰 KQ thật: `{result_str}`",
        f"",
        f"🧠 BẠN: `{user_str}`",
        f"   → {match_label(user_match, game_key)}",
        f"",
        f"🤖 AI: `{ai_str}`",
        f"   → {match_label(ai_match, game_key)}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ])

# ─────────────────────────────────────────────
# GỬI TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(text, token=None, chat_id=None):
    token = token or TELEGRAM_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"  ✅ Đã gửi Telegram ({len(text)} ký tự)")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi Telegram: {e}")
        return False

def send_daily_picks():
    data = load_data()
    analyses = {}
    for gkey in ["mega645", "power655", "max3d_plus", "lotto535"]:
        analyses[gkey] = analyze_game(gkey, data)
    msg = build_daily_picks_message(analyses)
    print(msg)  # In ra console để debug
    return msg, analyses

if __name__ == "__main__":
    msg, analyses = send_daily_picks()
    print("\n" + "="*60)
    print("👆 Đây là tin nhắn sẽ gửi về Telegram của bạn mỗi ngày")
