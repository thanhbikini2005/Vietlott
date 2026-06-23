"""
scraper_live.py — Fix parse ngày format DD/MM(...)YY từ lotto-8.com
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

def parse_date_lotto8(date_txt):
    """
    Parse ngày từ lotto-8.com
    Format thật: '20/06(Thứ bảy)26' hoặc '22/06(Thứ hai)26'
    DD/MM...YY (2 số cuối của năm)
    """
    # Tìm DD/MM
    m = re.search(r"(\d{1,2})/(\d{1,2})", date_txt)
    if not m:
        return None
    day   = int(m.group(1))
    month = int(m.group(2))

    # Tìm năm 2 chữ số ở cuối: ví dụ '26' → 2026
    y_match = re.search(r"\)(\d{2})$", date_txt.strip())
    if y_match:
        year = 2000 + int(y_match.group(1))
    else:
        # Fallback: đoán năm từ tháng
        now = datetime.now()
        year = now.year if month <= now.month else now.year - 1

    return f"{year}-{month:02d}-{day:02d}"

def parse_lotto8(html, game_key):
    """Parse table từ lotto-8.com với encoding fix"""
    # Fix encoding: lotto-8 trả về latin-1 nhưng content là UTF-8
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")

    soup    = BeautifulSoup(html, "html.parser")
    results = []
    today   = datetime.now().strftime("%Y-%m-%d")

    all_rows = soup.find_all("tr")
    print(f"  [{game_key}] rows={len(all_rows)}")

    for row in all_rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        date_txt = cells[0].get_text(" ", strip=True)
        nums_txt = cells[1].get_text(strip=True)

        date_str = parse_date_lotto8(date_txt)
        if not date_str:
            continue

        # Parse số: tách bằng dấu phẩy hoặc space, bỏ \xa0
        nums_clean = nums_txt.replace("\xa0", " ").replace(",", " ")
        nums = []
        for n in re.findall(r"\d+", nums_clean):
            val = int(n)
            if 1 <= val <= 99:
                nums.append(val)

        if not nums:
            continue

        results.append({"date": date_str, "numbers": sorted(nums)})

    today_recs = [r for r in results if r["date"] == today]
    print(f"  [{game_key}] parsed={len(results)}, today({today})={len(today_recs)}")
    for r in today_recs:
        print(f"  [{game_key}] ✅ KQ hôm nay: {r['numbers']}")

    return results

def parse_max3d_xskt(html):
    """
    Parse Max 3D+ từ xskt.com.vn
    Tìm bảng kết quả thật, không bị nhầm với số khác
    """
    soup  = BeautifulSoup(html, "html.parser")
    today = datetime.now().strftime("%Y-%m-%d")

    # Tìm trong bảng có chứa "Max 3D" hoặc kết quả dạng X-X-X
    # Ưu tiên tìm trong các thẻ có class liên quan đến kết quả
    result_divs = soup.find_all(class_=re.compile(r"result|ket-qua|winning|number", re.I))

    for div in result_divs:
        text = div.get_text(" ")
        # Pattern X-X-X chặt hơn: chỉ 1 chữ số mỗi vị trí
        pattern = re.findall(r"(?<!\d)([0-9])\s*[-–]\s*([0-9])\s*[-–]\s*([0-9])(?!\d)", text)
        if len(pattern) >= 2:
            bo1 = [int(pattern[0][0]), int(pattern[0][1]), int(pattern[0][2])]
            bo2 = [int(pattern[1][0]), int(pattern[1][1]), int(pattern[1][2])]
            print(f"  [max3d_plus] ✅ Parse OK: {bo1} | {bo2}")
            return [{"date": today, "bo1": bo1, "bo2": bo2}]

    # Fallback: tìm trong toàn trang nhưng lọc chặt hơn
    # Tìm chuỗi 6 chữ số đơn liên tiếp theo pattern bảng kết quả
    text = soup.get_text(" ")
    # Tìm pattern: 3 số đơn, khoảng cách, 3 số đơn
    m = re.search(
        r"(?<!\d)([0-9])\s*[-–]\s*([0-9])\s*[-–]\s*([0-9])"
        r".{0,30}"
        r"([0-9])\s*[-–]\s*([0-9])\s*[-–]\s*([0-9])(?!\d)",
        text
    )
    if m:
        bo1 = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
        bo2 = [int(m.group(4)), int(m.group(5)), int(m.group(6))]
        print(f"  [max3d_plus] ✅ Fallback OK: {bo1} | {bo2}")
        return [{"date": today, "bo1": bo1, "bo2": bo2}]

    print(f"  [max3d_plus] ❌ Không parse được kết quả")
    return []

def has_draws_today(game_key):
    return datetime.now().weekday() in SCHEDULE.get(game_key, [])

def scrape_latest(game_key, url):
    try:
        r = requests.get(f"{url}?indexpage=1&orderby=new", headers=HEADERS, timeout=20)
        r.raise_for_status()
        print(f"  [{game_key}] HTTP {r.status_code}, size={len(r.content)} bytes")
        # Dùng r.content (bytes) để tránh lỗi encoding
        return parse_lotto8(r.content, game_key)
    except Exception as e:
        print(f"  [{game_key}] ❌ {e}")
        return []

def scrape_max3d():
    sources = [
        ("xskt.com.vn",   "https://xskt.com.vn/xsmax3d"),
        ("atrungroi.com", "https://atrungroi.com/max3d-plus"),
    ]
    for name, url in sources:
        try:
            r = requests.get(url, headers={**HEADERS, "Referer": url}, timeout=20)
            r.raise_for_status()
            print(f"  [max3d_plus] {name}: HTTP {r.status_code}, size={len(r.content)} bytes")
            rows = parse_max3d_xskt(r.text)
            if rows:
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
    print(f"\n📅 {weekday_names[datetime.now().weekday()]} {today}")

    for gkey, url in SOURCES.items():
        if not has_draws_today(gkey):
            print(f"  [{gkey}] ⏭ Không quay hôm nay")
            continue
        print(f"\n  🔍 {gkey}...")
        rows = scrape_latest(gkey, url)
        kfn  = lambda r, g=gkey: make_key(g, r)
        data[gkey], added = merge(data.get(gkey,[]), rows, kfn)
        for r in added:
            if r.get("date") == today:
                sk = make_key(gkey, r)
                if sk not in sent:
                    new_results[gkey] = r
                    print(f"  🔔 MỚI: {gkey} → {r.get('numbers')}")
                else:
                    print(f"  ℹ️ Đã gửi: {gkey}")

    print(f"\n  🔍 max3d_plus...")
    max3d_rows = scrape_max3d()
    kfn3d = lambda r: make_key("max3d_plus", r)
    data["max3d_plus"], added = merge(data.get("max3d_plus",[]), max3d_rows, kfn3d)
    for r in added:
        if r.get("date") == today:
            sk = make_key("max3d_plus", r)
            if sk not in sent:
                new_results["max3d_plus"] = r
                print(f"  🔔 MỚI: max3d_plus → {r.get('bo1')} | {r.get('bo2')}")
            else:
                print(f"  ℹ️ Đã gửi: max3d_plus")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return new_results, data

def mark_as_sent(game_key, record):
    sent = load_sent()
    sent[make_key(game_key, record)] = datetime.now().isoformat()
    save_sent(sent)

if __name__ == "__main__":
    scrape_and_detect_new()
