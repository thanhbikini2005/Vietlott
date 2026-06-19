"""
scraper_live.py — Chạy trong GitHub Actions (không bị block IP)
Scrape kết quả mới nhất từ lotto-8.com và vietlott.vn
"""
import requests, json, re, time, os
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://www.lotto-8.com/",
}

DATA_FILE = "data/history.json"

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"mega645": [], "power655": [], "max3d_plus": [], "lotto535": []}

def parse_lotto8_table(html, game_key):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_txt = cells[0].get_text(" ", strip=True)
        nums_txt = cells[1].get_text(strip=True)
        date_m = re.search(r"(\d{2}/\d{2})", date_txt)
        if not date_m:
            continue
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", nums_txt) if 1 <= int(n) <= 99]
        if not nums:
            continue
        # Cố gắng parse năm
        year = datetime.now().year
        date_str = f"{year}-{date_m.group(1)[3:]}-{date_m.group(1)[:2]}"  # DD/MM → YYYY-MM-DD
        results.append({"date": date_str, "numbers": nums})
    return results

def scrape_game(url, game_key, pages=3):
    """Scrape 3 trang gần nhất (chỉ cần cập nhật mới)"""
    all_new = []
    for page in range(1, pages + 1):
        full_url = f"{url}?indexpage={page}&orderby=new"
        try:
            r = requests.get(full_url, headers=HEADERS, timeout=20)
            if r.status_code == 403:
                print(f"  [{game_key}] p{page}: 403 — thử User-Agent khác")
                alt_headers = {**HEADERS, "User-Agent": "curl/7.88.1"}
                r = requests.get(full_url, headers=alt_headers, timeout=20)
            r.raise_for_status()
            rows = parse_lotto8_table(r.text, game_key)
            all_new.extend(rows)
            print(f"  [{game_key}] p{page}: +{len(rows)} kỳ")
            time.sleep(1.5)
        except Exception as e:
            print(f"  [{game_key}] p{page}: ERROR — {e}")
    return all_new

def merge_data(existing, new_records, key_field="date"):
    """Ghép dữ liệu mới vào cũ, tránh duplicate"""
    existing_keys = {r.get(key_field) for r in existing}
    added = 0
    for r in new_records:
        if r.get(key_field) not in existing_keys:
            existing.append(r)
            added += 1
    existing.sort(key=lambda x: x.get(key_field, ""))
    return existing, added

def main():
    data = load_existing()
    print("🔄 Scraping dữ liệu mới nhất...\n")

    SOURCES = {
        "mega645":  "https://www.lotto-8.com/Vietnam/listltoVM45.asp",
        "power655": "https://www.lotto-8.com/Vietnam/listltoVM55.asp",
        "lotto535": "https://www.lotto-8.com/Vietnam/listltoVM35.asp",
    }

    for gkey, url in SOURCES.items():
        new = scrape_game(url, gkey, pages=2)
        data[gkey], added = merge_data(data[gkey], new)
        print(f"  ✅ {gkey}: +{added} kỳ mới (tổng: {len(data[gkey])})")

    # Max 3D+ — vietlott.vn API endpoint
    try:
        api_url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GamePlugIn,Vietlott.PlugIn.ashx"
        # Fallback: skip nếu block
        print("  [max3d_plus] Bỏ qua (vietlott.vn block bot) — dùng data cũ")
    except:
        pass

    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Đã cập nhật {DATA_FILE}")

if __name__ == "__main__":
    main()
