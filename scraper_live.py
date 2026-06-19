"""
scraper_live.py — Thu thập kết quả mới nhất từ web (chạy trong GitHub Actions)
"""
import requests, json, re, time, os
from datetime import datetime
from bs4 import BeautifulSoup
from analysis import BASE_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Referer":         "https://www.lotto-8.com/",
}

DATA_FILE = os.path.join(BASE_DIR, "data", "history.json")

SOURCES = {
    "mega645":  "https://www.lotto-8.com/Vietnam/listltoVM45.asp",
    "power655": "https://www.lotto-8.com/Vietnam/listltoVM55.asp",
    "lotto535": "https://www.lotto-8.com/Vietnam/listltoVM35.asp",
}

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"mega645": [], "power655": [], "max3d_plus": [], "lotto535": []}

def parse_table(html):
    soup    = BeautifulSoup(html, "html.parser")
    results = []
    year    = datetime.now().year
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_txt = cells[0].get_text(" ", strip=True)
        nums_txt = cells[1].get_text(strip=True)
        date_m = re.search(r"(\d{2})/(\d{2})", date_txt)
        if not date_m:
            continue
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", nums_txt) if 1 <= int(n) <= 99]
        if not nums:
            continue
        date_str = f"{year}-{date_m.group(2)}-{date_m.group(1)}"  # DD/MM → YYYY-MM-DD
        results.append({"date": date_str, "numbers": nums})
    return results

def scrape_game(url, game_key, pages=2):
    all_new = []
    for page in range(1, pages + 1):
        full_url = f"{url}?indexpage={page}&orderby=new"
        try:
            r = requests.get(full_url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            rows = parse_table(r.text)
            all_new.extend(rows)
            print(f"  [{game_key}] trang {page}: +{len(rows)} kỳ")
            time.sleep(1.5)
        except Exception as e:
            print(f"  [{game_key}] trang {page}: LỖI — {e}")
    return all_new

def merge(existing, new_records):
    keys  = {r.get("date") for r in existing}
    added = 0
    for r in new_records:
        if r.get("date") not in keys:
            existing.append(r)
            added += 1
    existing.sort(key=lambda x: x.get("date", ""))
    return existing, added

def main():
    data = load_existing()
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    print("🔄 Scraping kết quả mới nhất...\n")

    for gkey, url in SOURCES.items():
        new = scrape_game(url, gkey)
        data[gkey], added = merge(data.get(gkey, []), new)
        print(f"  ✅ {gkey}: +{added} kỳ mới (tổng: {len(data[gkey])})")

    print("  [max3d_plus] Giữ nguyên dữ liệu cũ")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã lưu {DATA_FILE}")

if __name__ == "__main__":
    main()
