"""
scraper_live.py — Scrape kết quả mới nhất, trả về True nếu có kết quả mới
Nguồn: lotto-8.com (Mega/Power/Lotto) + atrungroi.com (Max 3D+)
"""
import requests, json, re, time, os
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

# Max 3D+ — dùng atrungroi.com (không bị block)
MAX3D_URL = "https://atrungroi.com/max3dplus"

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

def parse_max3d_atrungroi(html):
    """
    Parse Max 3D+ từ atrungroi.com
    Kết quả dạng: 2 bộ 3 số, ví dụ: 4-6-8 | 1-2-3
    """
    soup    = BeautifulSoup(html, "html.parser")
    today   = datetime.now().strftime("%Y-%m-%d")
    results = []

    # Tìm tất cả số 3 chữ số dạng XXX liên tiếp trên trang
    text = soup.get_text(" ")
    # Tìm pattern ngày hôm nay và 6 chữ số 0-9 gần đó
    date_now = datetime.now().strftime("%d/%m/%Y")

    # Thử tìm bộ số dạng d-d-d
    pattern = re.findall(r"\b([0-9])[^\d]([0-9])[^\d]([0-9])\b", text)
    if len(pattern) >= 2:
        bo1 = [int(pattern[0][0]), int(pattern[0][1]), int(pattern[0][2])]
        bo2 = [int(pattern[1][0]), int(pattern[1][1]), int(pattern[1][2])]
        results.append({"date": today, "bo1": bo1, "bo2": bo2})
        return results

    # Fallback: tìm số 3 chữ số liên tiếp kiểu "123 456"
    nums3 = re.findall(r"\b(\d{3})\b", text)
    nums3 = [n for n in nums3 if all(int(c) <= 9 for c in n)]
    if len(nums3) >= 2:
        bo1 = [int(c) for c in nums3[0]]
        bo2 = [int(c) for c in nums3[1]]
        results.append({"date": today, "bo1": bo1, "bo2": bo2})

    return results

def scrape_latest(game_key, url):
    try:
        full_url = f"{url}?indexpage=1&orderby=new"
        r = requests.get(full_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        rows = parse_lotto8(r.text)
        print(f"  [{game_key}] ✅ {len(rows)} kỳ")
        return rows
    except Exception as e:
        print(f"  [{game_key}] ❌ LỖI: {e}")
        return []

def scrape_max3d_plus():
    """Thử nhiều nguồn cho Max 3D+"""
    sources = [
        ("atrungroi.com", "https://atrungroi.com/max3dplus"),
        ("xskt.com.vn",   "https://xskt.com.vn/xsmax3d"),
    ]
    for name, url in sources:
        try:
            r = requests.get(url, headers={**HEADERS, "Referer": url}, timeout=20)
            r.raise_for_status()
            rows = parse_max3d_atrungroi(r.text)
            if rows:
                print(f"  [max3d_plus] ✅ Lấy được từ {name}")
                return rows
            else:
                print(f"  [max3d_plus] ⚠️  {name}: không parse được kết quả")
        except Exception as e:
            print(f"  [max3d_plus] ❌ {name}: {e}")
    return []

def merge(existing, new_records, key="date"):
    keys  = {r.get(key) for r in existing}
    added = []
    for r in new_records:
        if r.get(key) not in keys:
            existing.append(r)
            added.append(r)
    existing.sort(key=lambda x: x.get(key, ""))
    return existing, added

def scrape_and_detect_new():
    """
    Scrape tất cả game, trả về dict các kết quả MỚI chưa gửi
    """
    data = load_existing()
    sent = load_sent()
    new_results = {}

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    # 3 game từ lotto-8.com
    for gkey, url in SOURCES.items():
        rows = scrape_latest(gkey, url)
        data[gkey], added = merge(data.get(gkey, []), rows)
        for r in added:
            sent_key = f"{gkey}_{r['date']}"
            if sent_key not in sent:
                new_results[gkey] = r
                print(f"  🔔 KQ MỚI: {gkey} ngày {r['date']}: {r.get('numbers')}")

    # Max 3D+
    max3d_rows = scrape_max3d_plus()
    data["max3d_plus"], added = merge(data.get("max3d_plus", []), max3d_rows, key="date")
    for r in added:
        sent_key = f"max3d_plus_{r['date']}"
        if sent_key not in sent:
            new_results["max3d_plus"] = r
            print(f"  🔔 KQ MỚI: max3d_plus ngày {r['date']}: {r.get('bo1')} | {r.get('bo2')}")

    # Lưu data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return new_results, data

def mark_as_sent(game_key, record):
    sent = load_sent()
    sent_key = f"{game_key}_{record.get('date', '')}"
    sent[sent_key] = datetime.now().isoformat()
    save_sent(sent)

if __name__ == "__main__":
    new, data = scrape_and_detect_new()
    if new:
        print(f"\n🔔 Có {len(new)} kết quả mới: {list(new.keys())}")
    else:
        print("\n⏳ Chưa có kết quả mới")
