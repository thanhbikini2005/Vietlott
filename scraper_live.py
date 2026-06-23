"""
scraper_live.py — Fix parse ngày + thêm debug log đầy đủ
"""
import requests, json, re, os
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

SCHEDULE = {
    "mega645":    [2, 4, 6],
    "power655":   [1, 3, 5],
    "max3d_plus": [0,1,2,3,4,5,6],
    "lotto535":   [0,1,2,3,4,5,6],
}

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"mega645":[], "power655":[], "max3d_plus":[], "lotto535":[]}

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
    nums = record.get("numbers", record.get("bo1", []))
    return f"{game_key}_{record.get('date','')}_{'-'.join(str(n) for n in sorted(nums))}"

def parse_lotto8(html, game_key):
    """
    Parse table từ lotto-8.com
    Format ngày trên web: DD/MM (ví dụ: 22/06)
    → chuyển thành YYYY-MM-DD
    """
    soup    = BeautifulSoup(html, "html.parser")
    results = []
    year    = datetime.now().year
    today   = datetime.now().strftime("%Y-%m-%d")

    # DEBUG: in raw HTML nếu không parse được
    all_rows = soup.find_all("tr")
    print(f"  [{game_key}] HTML rows: {len(all_rows)}")

    for i, row in enumerate(all_rows[:5]):  # debug 5 rows đầu
        cells = row.find_all("td")
        if cells:
            raw = [c.get_text(strip=True) for c in cells[:3]]
            print(f"  [{game_key}] Row {i}: {raw}")

    for row in all_rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        date_txt = cells[0].get_text(" ", strip=True)
        nums_txt = cells[1].get_text(strip=True)

        # Tìm format DD/MM trong ô ngày
        m = re.search(r"(\d{1,2})/(\d{1,2})", date_txt)
        if not m:
            continue

        day   = int(m.group(1))
        month = int(m.group(2))

        # Xác định năm (nếu tháng lớn hơn tháng hiện tại → năm ngoái)
        cur_month = datetime.now().month
        y = year if month <= cur_month else year - 1
        date_str = f"{y}-{month:02d}-{day:02d}"

        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", nums_txt) if 1 <= int(n) <= 99]
        if not nums:
            continue

        results.append({"date": date_str, "numbers": nums})

    today_recs = [r for r in results if r["date"] == today]
    print(f"  [{game_key}] Parse OK: {len(results)} kỳ, hôm nay ({today}): {len(today_recs)} kỳ")
    if today_recs:
        print(f"  [{game_key}] KQ hôm nay: {today_recs[0]['numbers']}")

    return results

def parse_max3d(html):
    soup  = BeautifulSoup(html, "html.parser")
    today = datetime.now().strftime("%Y-%m-%d")
    text  = soup.get_text(" ")
    print(f"  [max3d_plus] HTML size: {len(html)} bytes")

    # Pattern: X-X-X hoặc X – X – X
    pattern = re.findall(r"\b([0-9])\s*[-–]\s*([0-9])\s*[-–]\s*([0-9])\b", text)
    print(f"  [max3d_plus] Pattern tìm được: {pattern[:5]}")

    if len(pattern) >= 2:
        bo1 = [int(pattern[0][0]), int(pattern[0][1]), int(pattern[0][2])]
        bo2 = [int(pattern[1][0]), int(pattern[1][1]), int(pattern[1][2])]
        print(f"  [max3d_plus] KQ: bo1={bo1} bo2={bo2}")
        return [{"date": today, "bo1": bo1, "bo2": bo2}]

    # Fallback: XXX liên tiếp
    nums3 = [n for n in re.findall(r"\b(\d{3})\b", text) if all(int(c)<=9 for c in n)]
    print(f"  [max3d_plus] Fallback nums3: {nums3[:5]}")
    if len(nums3) >= 2:
        return [{"date": today,
                 "bo1": [int(c) for c in nums3[0]],
                 "bo2": [int(c) for c in nums3[1]]}]
    return []

def has_draws_today(game_key):
    return datetime.now().weekday() in SCHEDULE.get(game_key, [])

def scrape_latest(game_key, url):
    try:
        r = requests.get(f"{url}?indexpage=1&orderby=new", headers=HEADERS, timeout=20)
        r.raise_for_status()
        print(f"  [{game_key}] HTTP {r.status_code}, size={len(r.text)} bytes")
        return parse_lotto8(r.text, game_key)
    except Exception as e:
        print(f"  [{game_key}] ❌ {e}")
        return []

def scrape_max3d():
    for name, url in [
        ("atrungroi.com", "https://atrungroi.com/max3dplus"),
        ("xskt.com.vn",   "https://xskt.com.vn/xsmax3d"),
    ]:
        try:
            r = requests.get(url, headers={**HEADERS, "Referer": url}, timeout=20)
            r.raise_for_status()
            rows = parse_max3d(r.text)
            if rows:
                print(f"  [max3d_plus] ✅ {name}")
                return rows
        except Exception as e:
            print(f"  [max3d_plus] ❌ {name}: {e}")
    return []

def merge(existing, new_records, key_fn):
    keys  = {key_fn(r) for r in existing}
    added = []
    for r in new_records:
        if key_fn(r) not in keys:
            existing.append(r)
            added.append(r)
    existing.sort(key=lambda x: x.get("date",""))
    return existing, added

def scrape_and_detect_new():
    data  = load_existing()
    sent  = load_sent()
    today = datetime.now().strftime("%Y-%m-%d")
    new_results = {}

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    weekday_names = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    print(f"\n📅 Hôm nay: {weekday_names[datetime.now().weekday()]} {today}")

    for gkey, url in SOURCES.items():
        if not has_draws_today(gkey):
            print(f"\n  [{gkey}] ⏭ Không có lịch quay hôm nay")
            continue
        print(f"\n  🔍 Scraping {gkey}...")
        rows = scrape_latest(gkey, url)
        kfn  = lambda r, g=gkey: make_key(g, r)
        data[gkey], added = merge(data.get(gkey,[]), rows, kfn)
        for r in added:
            if r.get("date") == today:
                sk = make_key(gkey, r)
                if sk not in sent:
                    new_results[gkey] = r
                    print(f"  🔔 KQ MỚI → {gkey}: {r.get('numbers')}")
                else:
                    print(f"  ℹ️ Đã gửi rồi: {gkey}")

    # Max 3D+
    print(f"\n  🔍 Scraping max3d_plus...")
    max3d_rows = scrape_max3d()
    kfn3d = lambda r: make_key("max3d_plus", r)
    data["max3d_plus"], added = merge(data.get("max3d_plus",[]), max3d_rows, kfn3d)
    for r in added:
        if r.get("date") == today:
            sk = make_key("max3d_plus", r)
            if sk not in sent:
                new_results["max3d_plus"] = r
                print(f"  🔔 KQ MỚI → max3d_plus: {r.get('bo1')} | {r.get('bo2')}")
            else:
                print(f"  ℹ️ Đã gửi rồi: max3d_plus")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'🔔 Có ' + str(len(new_results)) + ' KQ mới: ' + str(list(new_results.keys())) if new_results else '⏳ Không có KQ mới hôm nay'}")
    return new_results, data

def mark_as_sent(game_key, record):
    sent = load_sent()
    sent[make_key(game_key, record)] = datetime.now().isoformat()
    save_sent(sent)

if __name__ == "__main__":
    scrape_and_detect_new()
