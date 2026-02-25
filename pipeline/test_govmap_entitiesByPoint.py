import json, os, requests

URL = "https://www.govmap.gov.il/api/layers-catalog/entitiesByPoint"

with open("pipeline/govmap_entitiesByPoint_payload.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

# (אופציונלי) אם תרצה לנסות להוסיף את ה-token של המפה שלך לבקשה:
govmap_token = os.getenv("GOVMAP_TOKEN", "").strip()
if govmap_token and "token" not in payload:
    payload["token"] = govmap_token

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.govmap.gov.il",
    "Referer": "https://www.govmap.gov.il/",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# אם בסוף נצטרך cookie (רק אם עדיין 401)
cookie = os.getenv("GOVMAP_COOKIE", "").strip()
if cookie:
    headers["Cookie"] = cookie

r = requests.post(URL, json=payload, headers=headers, timeout=60)
print("status:", r.status_code)
print("body (first 4000):")
print(r.text[:4000])
r.raise_for_status()

data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2)[:20000])
