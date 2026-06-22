"""
scraper_live.py — Scrape kết quả mới nhất, detect kết quả chưa gửi
Fix: dùng (game + date + numbers) làm key thay vì chỉ date
"""
import requests, json, re, time, os, hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from analysis import BASE_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": "https://www.lotto-8.com/",
}

DATA_FILE = os.path.join(BASE_DIR, "data", "history.json")
SENT_FILE = os.path.join(BASE_DIR, "data", "sent_results.json")

SOURCES = {
    "mega645":  "https://www.lotto-8.com/Vietnam/listltoVM45.asp",
    "power655": "https://www.lotto-8.com/Vietnam/listltoVM55.asp",
    "lotto535": "https://www.lotto-8.com/Vietnam/listltoVM35.asp",
}

# Lịch quay — để biết hôm nay có game nào không
SCHEDULE = {
    "mega645":    [2, 4, 6],        # Thứ 4, 6, CN (weekday: Wed=2, Fri=4, Sun=6)
    "power655":   [1, 3, 5],        # Thứ 3, 5, 7 (Tue=1, Thu=3, Sat=5)
    "max3d_plus": [0, 1, 2, 3, 4, 5, 6],  # Mỗi ngày
    "lotto535":   [0, 1, 2, 3, 4, 5, 6],  # Mỗi ngày
}

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"mega645": [], "power655": [], "max3d_plus": [], "lotto535": []}

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_sent(sent):
    os.makedirs(os.path.dirname(SENT_FILE), exist_ok=True)
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(sent, f, indent=2)

def make_key(game_key, record):
    """Key unique = game + date + hash(numbers) — tránh duplicate"""
    nums = record.get("numbers", record.get("bo1", []))
    nums_str = "-".join(str(n) for n in sorted(nums))
    return f"{game_key}_{record.get('date', '')}_{nums_str}"

def parse_lotto8(html):
    soup    = BeautifulSoup(html, "html.parser")
    results = []
    year    = datetime.now().year
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_txt = cells[0].get_text(" ", strip=True)
        nums_txt = cells[1].get_text(strip=True)
        m = re.search(r"(\d{2})/(\d{2})", date_txt)
        if not m:
            continue
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", nums_txt) if 1 <= int(n) <= 99]
        if not nums:
            continue
        date_str = f"{year}-{m.group(2)}-{m.group(1)}"
        results.append({"date": date_str, "numbers": nums})
    return results

def parse_max3d(html):
    soup    = BeautifulSoup(html, "html.parser")
    today   = datetime.now().strftime("%Y-%m-%d")
    text    = soup.get_text(" ")
    # Tìm pattern X-X-X (3 chữ số cách nhau bằng dấu gạch hoặc space)
    pattern = re.findall(r"\b([0-9])\s*[-–]\s*([0-9])\s*[-–]\s*([0-9])\b", text)
    if len(pattern) >= 2:
        bo1 = [int(pattern[0][0]), int(pattern[0][1]), int(pattern[0][2])]
        bo2 = [int(pattern[1][0]), int(pattern[1][1]), int(pattern[1][2])]
        return [{"date": today, "bo1": bo1, "bo2": bo2}]
    # Fallback: số 3 chữ số liên tiếp (mỗi chữ số 0-9)
    nums3 = re.findall(r"\b([0-9]{3})\b", text)
    if len(nums3) >= 2:
        return [{"date": today,
                 "bo1": [int(c) for c in nums3[0]],
                 "bo2": [int(c) for c in nums3[1]]}]
    return []

def has_draws_today(game_key):
    """Kiểm tra hôm nay có lịch quay không"""
    weekday = datetime.now().weekday()  # Mon=0 ... Sun=6
    return weekday in SCHEDULE.get(game_key, [])

def scrape_latest(game_key, url):
    try:
        r = requests.get(f"{url}?indexpage=1&orderby=new", headers=HEADERS, timeout=20)
        r.raise_for_status()
        rows = parse_lotto8(r.text)
        print(f"  [{game_key}] ✅ {len(rows)} kỳ gần nhất")
        return rows
    except Exception as e:
        print(f"  [{game_key}] ❌ {e}")
        return []

def scrape_max3d():
    sources = [
        ("atrungroi.com", "https://atrungroi.com/max3dplus"),
        ("xskt.com.vn",   "https://xskt.com.vn/xsmax3d"),
    ]
    for name, url in sources:
        try:
            r = requests.get(url, headers={**HEADERS, "Referer": url}, timeout=20)
            r.raise_for_status()
            rows = parse_max3d(r.text)
            if rows:
                print(f"  [max3d_plus] ✅ OK từ {name}")
                return rows
            print(f"  [max3d_plus] ⚠️ {name}: không parse được")
        except Exception as e:
            print(f"  [max3d_plus] ❌ {name}: {e}")
    return []

def merge(existing, new_records, key_fn):
    existing_keys = {key_fn(r) for r in existing}
    added = []
    for r in new_records:
        if key_fn(r) not in existing_keys:
            existing.append(r)
            added.append(r)
    existing.sort(key=lambda x: x.get("date", ""))
    return existing, added

def scrape_and_detect_new():
    data = load_existing()
    sent = load_sent()
    today = datetime.now().strftime("%Y-%m-%d")
    new_results = {}

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    for gkey, url in SOURCES.items():
        if not has_draws_today(gkey):
            print(f"  [{gkey}] ⏭ Hôm nay không có lịch quay")
            continue
        rows = scrape_latest(gkey, url)
        key_fn = lambda r: make_key(gkey, r)
        data[gkey], added = merge(data.get(gkey, []), rows, key_fn)
        for r in added:
            if r.get("date") == today:
                sent_key = make_key(gkey, r)
                if sent_key not in sent:
                    new_results[gkey] = r
                    print(f"  🔔 MỚI: {gkey} {today} → {r.get('numbers')}")

    # Max 3D+
    max3d_rows = scrape_max3d()
    key_fn_3d = lambda r: make_key("max3d_plus", r)
    data["max3d_plus"], added = merge(data.get("max3d_plus", []), max3d_rows, key_fn_3d)
    for r in added:
        if r.get("date") == today:
            sent_key = make_key("max3d_plus", r)
            if sent_key not in sent:
                new_results["max3d_plus"] = r
                print(f"  🔔 MỚI: max3d_plus {today} → {r.get('bo1')} | {r.get('bo2')}")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not new_results:
        # In rõ lý do tại sao không có gì mới
        weekday_names = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
        today_name = weekday_names[datetime.now().weekday()]
        print(f"\n  📅 Hôm nay {today_name} {today}:")
        for gkey in ["mega645","power655","max3d_plus","lotto535"]:
            has = has_draws_today(gkey)
            print(f"     {'✅' if has else '❌'} {gkey}: {'có lịch quay' if has else 'không quay hôm nay'}")

    return new_results, data

def mark_as_sent(game_key, record):
    sent = load_sent()
    sent[make_key(game_key, record)] = datetime.now().isoformat()
    save_sent(sent)

if __name__ == "__main__":
    new, _ = scrape_and_detect_new()
    print(f"\n{'🔔 ' + str(len(new)) + ' kết quả mới: ' + str(list(new.keys())) if new else '⏳ Không có kết quả mới'}")
