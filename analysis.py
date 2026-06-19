"""
analysis.py — Phân tích thống kê lịch sử Vietlott
Tạo 2 bộ số: [BẠN] từ thống kê, [AI] từ logic nguội/nóng
"""

import json
from collections import Counter
from datetime import datetime, timedelta

def load_data():
    with open("/home/claude/vietlott-bot/data/history.json", encoding="utf-8") as f:
        return json.load(f)

# ─────────────────────────────────────────────
# PHÂN TÍCH THEO THỜI GIAN
# ─────────────────────────────────────────────
def filter_by_period(records, period="month"):
    """Lọc theo tuần/tháng/quý/năm hiện tại"""
    now = datetime.now()
    filtered = []
    for r in records:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
        except:
            continue
        if period == "week":
            start = now - timedelta(days=now.weekday() + 7*4)  # 4 tuần gần nhất
            if d >= start:
                filtered.append(r)
        elif period == "month":
            if d.month == now.month and d.year == now.year:
                filtered.append(r)
            elif d.month == now.month - 1 and d.year == now.year:
                filtered.append(r)
        elif period == "quarter":
            q = (now.month - 1) // 3
            if (d.month - 1) // 3 == q and d.year == now.year:
                filtered.append(r)
        elif period == "year":
            if d.year == now.year:
                filtered.append(r)
        elif period == "all":
            filtered.append(r)
    return filtered

def position_analysis(records, game="mega645"):
    """Phân tích vị trí: đầu, cạnh đầu, giữa, cạnh cuối, cuối"""
    if game in ["mega645", "power655", "lotto535"]:
        pos = {"dau": [], "can_dau": [], "giua": [], "can_cuoi": [], "cuoi": []}
        for r in records:
            nums = sorted(r.get("numbers", []))
            if not nums:
                continue
            n = len(nums)
            if n >= 1: pos["dau"].append(nums[0])
            if n >= 2: pos["can_dau"].append(nums[1])
            if n >= 3: pos["giua"].append(nums[n//2])
            if n >= 4: pos["can_cuoi"].append(nums[-2])
            if n >= 1: pos["cuoi"].append(nums[-1])
        return {k: Counter(v).most_common(5) for k, v in pos.items()}
    return {}

def freq_analysis(records, game="mega645"):
    """Tần suất xuất hiện của từng số"""
    counter = Counter()
    for r in records:
        nums = r.get("numbers", [])
        counter.update(nums)
    return counter

# ─────────────────────────────────────────────
# CHỌN SỐ THEO CÔNG THỨC
# ─────────────────────────────────────────────
def pick_user_numbers(game, records, n_pick):
    """[BẠN] — Chọn theo tần suất cao nhất + phân tích vị trí"""
    # Tần suất theo tháng + quý + năm
    month_recs = filter_by_period(records, "month")
    quarter_recs = filter_by_period(records, "quarter")
    year_recs = filter_by_period(records, "year")
    all_recs = records[-120:]  # 120 kỳ gần nhất

    # Đếm tần suất có trọng số
    freq = Counter()
    for r in month_recs:
        for n in r.get("numbers", []):
            freq[n] += 4  # Tháng: trọng số cao
    for r in quarter_recs:
        for n in r.get("numbers", []):
            freq[n] += 2  # Quý
    for r in year_recs:
        for n in r.get("numbers", []):
            freq[n] += 1  # Năm
    for r in all_recs:
        for n in r.get("numbers", []):
            freq[n] += 1

    top = [num for num, _ in freq.most_common(n_pick * 3)]
    # Đảm bảo phân bố: lấy từ đầu + giữa + cuối phạm vi
    pos = position_analysis(records, game)
    must_have = set()
    if pos:
        for pkey in ["dau", "giua", "cuoi"]:
            if pos.get(pkey):
                must_have.add(pos[pkey][0][0])

    result = list(must_have)
    for n in top:
        if n not in result:
            result.append(n)
        if len(result) >= n_pick:
            break

    return sorted(result[:n_pick])

def pick_ai_numbers(game, records, n_pick, max_num):
    """[AI] — Chọn số 'nguội' (lâu không ra) + phân phối đều"""
    last_seen = {}
    for i, r in enumerate(records):
        for n in r.get("numbers", []):
            last_seen[n] = i

    total = len(records)
    # Điểm = số kỳ chưa ra (nhiều = nguội = có thể sắp ra)
    scores = {}
    for n in range(1, max_num + 1):
        if n in last_seen:
            scores[n] = total - last_seen[n]
        else:
            scores[n] = total + 50  # Chưa ra lần nào

    # Chọn top nguội nhất
    candidates = sorted(scores.items(), key=lambda x: -x[1])
    # Đảm bảo phân bố: chia max_num thành 3 vùng
    third = max_num // 3
    zones = [
        [n for n, _ in candidates if n <= third],
        [n for n, _ in candidates if third < n <= 2*third],
        [n for n, _ in candidates if n > 2*third],
    ]

    result = []
    per_zone = n_pick // 3
    for zone in zones:
        result.extend(zone[:per_zone])
    # Bổ sung nếu thiếu
    for n, _ in candidates:
        if n not in result:
            result.append(n)
        if len(result) >= n_pick:
            break

    return sorted(result[:n_pick])

# ─────────────────────────────────────────────
# PHÂN TÍCH ĐẦY ĐỦ CHO 1 GAME
# ─────────────────────────────────────────────
def analyze_game(game_key, data):
    records = data.get(game_key, [])
    if not records:
        return None

    GAME_CONFIG = {
        "mega645": {"name": "Mega 6/45", "n": 6, "max": 45},
        "power655": {"name": "Power 6/55", "n": 6, "max": 55},
        "max3d_plus": {"name": "Max 3D+", "n": 3, "max": 9},
        "lotto535": {"name": "Lotto 5/35", "n": 5, "max": 35},
    }
    cfg = GAME_CONFIG[game_key]

    # Thống kê vị trí theo từng chu kỳ
    pos_week = position_analysis(filter_by_period(records, "week"), game_key)
    pos_month = position_analysis(filter_by_period(records, "month"), game_key)
    pos_quarter = position_analysis(filter_by_period(records, "quarter"), game_key)
    pos_year = position_analysis(filter_by_period(records, "year"), game_key)

    # Tần suất tổng
    freq_all = freq_analysis(records)
    freq_month = freq_analysis(filter_by_period(records, "month"))

    # Chọn số
    if game_key == "max3d_plus":
        user_bo1 = [records[-1]["bo1"]] if records else [[0,0,0]]
        user_bo2 = [records[-1]["bo2"]] if records else [[0,0,0]]
        ai_bo1 = [sorted([abs(9-n) for n in (records[-1]["bo1"] if records else [1,2,3])])]
        ai_bo2 = [sorted([abs(9-n) for n in (records[-1]["bo2"] if records else [4,5,6])])]
        user_pick = {"bo1": [4,7,2], "bo2": [1,5,8]}
        ai_pick = {"bo1": [0,3,9], "bo2": [6,2,5]}
    else:
        user_pick = pick_user_numbers(game_key, records, cfg["n"])
        ai_pick = pick_ai_numbers(game_key, records, cfg["n"], cfg["max"])

    return {
        "name": cfg["name"],
        "total_records": len(records),
        "freq_top10_all": freq_all.most_common(10),
        "freq_top10_month": freq_month.most_common(10),
        "position": {
            "week": pos_week,
            "month": pos_month,
            "quarter": pos_quarter,
            "year": pos_year,
        },
        "user_pick": user_pick,
        "ai_pick": ai_pick,
    }

if __name__ == "__main__":
    data = load_data()
    for gkey in ["mega645", "power655", "max3d_plus", "lotto535"]:
        result = analyze_game(gkey, data)
        if not result:
            continue
        print(f"\n{'='*50}")
        print(f"🎯 {result['name']} — {result['total_records']} kỳ")
        print(f"  Top số hay ra (tháng này): {result['freq_top10_month'][:5]}")
        print(f"  Số đầu hay ra: {result['position']['month'].get('dau', [])[:3]}")
        print(f"  Số cuối hay ra: {result['position']['month'].get('cuoi', [])[:3]}")
        print(f"  [BẠN] chọn: {result['user_pick']}")
        print(f"  [AI]  chọn: {result['ai_pick']}")

    print("\n✅ Phân tích xong!")
