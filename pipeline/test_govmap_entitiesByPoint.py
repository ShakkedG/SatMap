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

    def do_try(tag, p):
        r = requests.post(URL, json=p, headers=headers, timeout=60)
        print("\n==", tag, "==")
        print("status:", r.status_code)
        txt = r.text[:500]
        print("body(first500):", txt)
        if r.ok:
            try:
                j = r.json()
                data = j.get("data", None)
                print("data_len:", len(data) if isinstance(data, list) else type(data))
            except Exception as e:
                print("json parse error:", e)

    # try original
    do_try("original", payload)

    # try bigger tolerances
    for t in (30, 80, 120, 200):
        p2 = dict(payload)
        p2["tolerance"] = t
        do_try(f"tolerance={t}", p2)

    # try swapped point
    if isinstance(payload.get("point"), list) and len(payload["point"]) == 2:
        p3 = dict(payload)
        p3["point"] = [payload["point"][1], payload["point"][0]]
        do_try("swapped_xy", p3)

if __name__ == "__main__":
    main()
