"""
analysis.py — Phân tích thống kê lịch sử Vietlott
Tạo 2 bộ số: [BẠN] từ thống kê, [AI] từ logic nguội/nóng
"""

import json, os, random
from collections import Counter
from datetime import datetime, timedelta

# ── Đường dẫn tương đối (chạy đúng cả local lẫn GitHub Actions) ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "history.json")

def generate_seed_data():
    """Tạo dữ liệu lịch sử mẫu nếu chưa có file thật"""
    random.seed(2024)
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    def gen_records(start_date, count, n_nums, max_num, has_special=False):
        records = []
        d = start_date
        for i in range(count):
            nums = sorted(random.sample(range(1, max_num + 1), n_nums))
            r = {"date": d.strftime("%Y-%m-%d"), "ky": i + 1, "numbers": nums}
            if has_special:
                sp = random.randint(1, max_num)
                while sp in nums:
                    sp = random.randint(1, max_num)
                r["special"] = sp
            records.append(r)
            d += timedelta(days=random.choice([2, 2, 3]))
        return records

    def gen_max3d(start_date, count):
        records = []
        d = start_date
        for i in range(count):
            records.append({
                "date": d.strftime("%Y-%m-%d"),
                "ky": i + 1,
                "bo1": [random.randint(0, 9) for _ in range(3)],
                "bo2": [random.randint(0, 9) for _ in range(3)],
            })
            d += timedelta(days=random.choice([1, 2]))
        return records

    data = {
        "mega645":   gen_records(datetime(2023, 1, 4),  420, 6, 45),
        "power655":  gen_records(datetime(2023, 1, 3),  410, 6, 55, has_special=True),
        "max3d_plus": gen_max3d(datetime(2023, 1, 3),   300),
        "lotto535":  gen_records(datetime(2025, 6, 29), 700, 5, 35),
        "meta": {"generated": datetime.now().isoformat(), "is_seed": True}
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Đã tạo seed data tại {DATA_FILE}")
    return data

def load_data():
    if not os.path.exists(DATA_FILE):
        print("⚠️  Không tìm thấy history.json — tạo seed data...")
        return generate_seed_data()
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

# ─────────────────────────────────────────────
# PHÂN TÍCH THEO THỜI GIAN
# ─────────────────────────────────────────────
def filter_by_period(records, period="month"):
    now = datetime.now()
    filtered = []
    for r in records:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
        except:
            continue
        if period == "week":
            start = now - timedelta(days=now.weekday() + 28)
            if d >= start:
                filtered.append(r)
        elif period == "month":
            if d.month == now.month and d.year == now.year:
                filtered.append(r)
            elif d.month == (now.month - 1 or 12) and d.year == (now.year if now.month > 1 else now.year - 1):
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
    if game not in ["mega645", "power655", "lotto535"]:
        return {}
    pos = {"dau": [], "can_dau": [], "giua": [], "can_cuoi": [], "cuoi": []}
    for r in records:
        nums = sorted(r.get("numbers", []))
        if not nums:
            continue
        n = len(nums)
        pos["dau"].append(nums[0])
        if n >= 2: pos["can_dau"].append(nums[1])
        if n >= 3: pos["giua"].append(nums[n // 2])
        if n >= 4: pos["can_cuoi"].append(nums[-2])
        pos["cuoi"].append(nums[-1])
    return {k: Counter(v).most_common(5) for k, v in pos.items()}

def freq_analysis(records):
    counter = Counter()
    for r in records:
        counter.update(r.get("numbers", []))
    return counter

# ─────────────────────────────────────────────
# CHỌN SỐ
# ─────────────────────────────────────────────
def pick_user_numbers(game, records, n_pick):
    month_recs   = filter_by_period(records, "month")
    quarter_recs = filter_by_period(records, "quarter")
    year_recs    = filter_by_period(records, "year")
    recent_recs  = records[-120:]

    freq = Counter()
    for r in month_recs:
        for n in r.get("numbers", []): freq[n] += 4
    for r in quarter_recs:
        for n in r.get("numbers", []): freq[n] += 2
    for r in year_recs:
        for n in r.get("numbers", []): freq[n] += 1
    for r in recent_recs:
        for n in r.get("numbers", []): freq[n] += 1

    pos = position_analysis(records, game)
    must_have = set()
    if pos:
        for pkey in ["dau", "giua", "cuoi"]:
            if pos.get(pkey):
                must_have.add(pos[pkey][0][0])

    result = list(must_have)
    for num, _ in freq.most_common(n_pick * 3):
        if num not in result:
            result.append(num)
        if len(result) >= n_pick:
            break

    return sorted(result[:n_pick])

def pick_ai_numbers(game, records, n_pick, max_num):
    last_seen = {}
    for i, r in enumerate(records):
        for n in r.get("numbers", []):
            last_seen[n] = i

    total = len(records)
    scores = {}
    for n in range(1, max_num + 1):
        scores[n] = (total - last_seen[n]) if n in last_seen else (total + 50)

    candidates = sorted(scores.items(), key=lambda x: -x[1])
    third = max_num // 3
    zones = [
        [n for n, _ in candidates if n <= third],
        [n for n, _ in candidates if third < n <= 2 * third],
        [n for n, _ in candidates if n > 2 * third],
    ]

    result = []
    for zone in zones:
        result.extend(zone[: n_pick // 3])
    for n, _ in candidates:
        if n not in result:
            result.append(n)
        if len(result) >= n_pick:
            break

    return sorted(result[:n_pick])

def pick_max3d(records):
    """Chọn bộ số Max 3D+ dựa trên tần suất vị trí"""
    pos_freq = [{} for _ in range(6)]  # 3 vị trí bo1 + 3 vị trí bo2
    for r in records[-100:]:
        for j, n in enumerate(r.get("bo1", [])):
            pos_freq[j][n] = pos_freq[j].get(n, 0) + 1
        for j, n in enumerate(r.get("bo2", [])):
            pos_freq[j + 3][n] = pos_freq[j + 3].get(n, 0) + 1

    def best(d):
        return max(d, key=d.get) if d else random.randint(0, 9)

    user_bo1 = [best(pos_freq[i]) for i in range(3)]
    user_bo2 = [best(pos_freq[i + 3]) for i in range(3)]
    # AI: số ít ra nhất tại mỗi vị trí
    def coldest(d):
        all_nums = set(range(10))
        unseen = all_nums - set(d.keys())
        if unseen: return min(unseen)
        return min(d, key=d.get)
    ai_bo1 = [coldest(pos_freq[i]) for i in range(3)]
    ai_bo2 = [coldest(pos_freq[i + 3]) for i in range(3)]
    return {"user": {"bo1": user_bo1, "bo2": user_bo2},
            "ai":   {"bo1": ai_bo1,   "bo2": ai_bo2}}

# ─────────────────────────────────────────────
# PHÂN TÍCH ĐẦY ĐỦ
# ─────────────────────────────────────────────
def analyze_game(game_key, data):
    records = data.get(game_key, [])
    if not records:
        return None

    GAME_CONFIG = {
        "mega645":   {"name": "Mega 6/45",  "n": 6, "max": 45},
        "power655":  {"name": "Power 6/55", "n": 6, "max": 55},
        "max3d_plus":{"name": "Max 3D+",    "n": 3, "max": 9},
        "lotto535":  {"name": "Lotto 5/35", "n": 5, "max": 35},
    }
    cfg = GAME_CONFIG[game_key]

    if game_key == "max3d_plus":
        picks = pick_max3d(records)
        return {
            "name": cfg["name"],
            "total_records": len(records),
            "freq_top10_all": [],
            "freq_top10_month": [],
            "position": {"week": {}, "month": {}, "quarter": {}, "year": {}},
            "user_pick": picks["user"],
            "ai_pick":   picks["ai"],
        }

    pos_month   = position_analysis(filter_by_period(records, "month"),   game_key)
    pos_quarter = position_analysis(filter_by_period(records, "quarter"), game_key)
    pos_year    = position_analysis(filter_by_period(records, "year"),    game_key)
    pos_week    = position_analysis(filter_by_period(records, "week"),    game_key)

    freq_all   = freq_analysis(records)
    freq_month = freq_analysis(filter_by_period(records, "month"))

    return {
        "name": cfg["name"],
        "total_records": len(records),
        "freq_top10_all":   freq_all.most_common(10),
        "freq_top10_month": freq_month.most_common(10),
        "position": {
            "week":    pos_week,
            "month":   pos_month,
            "quarter": pos_quarter,
            "year":    pos_year,
        },
        "user_pick": pick_user_numbers(game_key, records, cfg["n"]),
        "ai_pick":   pick_ai_numbers(game_key, records, cfg["n"], cfg["max"]),
    }
