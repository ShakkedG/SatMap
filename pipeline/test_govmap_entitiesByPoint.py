import os
import json
import requests

URL = "https://www.govmap.gov.il/api/layers-catalog/entitiesByPoint"
PAYLOAD_PATH = "pipeline/govmap_entitiesByPoint_payload.json"

def load_payload():
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_headers():
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

    cookie = os.getenv("GOVMAP_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie

    # אופציונלי: אם תרצה לנסות גם טוקן (לא חובה אם cookie עובד)
    # token = os.getenv("GOVMAP_TOKEN", "").strip()
    # if token:
    #     headers["x-govmap-token"] = token

    return headers

def main():
    payload = load_payload()
    headers = build_headers()

    r = requests.post(URL, json=payload, headers=headers, timeout=60)

    print("status:", r.status_code)
    print("content-type:", r.headers.get("content-type", ""))
    print("body (first 2000 chars):")
    print(r.text[:2000])

    r.raise_for_status()

    # אם התשובה JSON — נדפיס מבנה גדול יותר (עד 20k תווים)
    try:
        data = r.json()
        print("\njson (first 20000 chars pretty):")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:20000])
    except Exception:
        print("\nResponse is not JSON (or failed to parse JSON).")

if __name__ == "__main__":
    main()
