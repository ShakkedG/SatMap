#!/usr/bin/env python3
import os
import json
import time
import requests

# ========= ENV =========
EDL_TOKEN = os.getenv("EDL_TOKEN", "").strip()
HYP3_API_URL = os.getenv("HYP3_API_URL", "https://hyp3-api.asf.alaska.edu").strip()

# בקוד שלך כבר יש "Pairs fetched: X" – תשאיר את הפונקציה שמביאה pairs כמו שהיא,
# ופשוט תשתמש ב-submit_hyp3_jobs(pairs) למטה כדי לשלוח ל-HyP3.

TIMEOUT = 90


def _headers():
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN (GitHub Actions secret).")
    return {
        "Authorization": f"Bearer {EDL_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _pick_root(base: str) -> str:
    """
    HyP3 מפרסם שרתים גם ב- / וגם ב- /api (תלוי בפריסה).
    נבדוק GET /user כדי לבחור root תקין (200/401/403 אומר שהנתיב קיים).
    """
    base = base.rstrip("/")
    candidates = [base, f"{base}/api"]

    h = _headers()
    for root in candidates:
        url = f"{root}/user"
        try:
            r = requests.get(url, headers=h, timeout=30)
            print(f"[HyP3] probe {url} -> {r.status_code}")
            if r.status_code != 404:
                # 200 = מאומת, 401/403 = נתיב קיים אבל טוקן לא תקין/לא הוזן
                return root
        except Exception as e:
            print(f"[HyP3] probe failed for {url}: {e}")

    # אם איכשהו הכל נכשל – נחזיר base וננסה בכל זאת
    return base


def submit_hyp3_jobs(jobs_payload: dict) -> dict:
    """
    jobs_payload חייב להיות בפורמט:
    { "jobs": [ { "name": "...", "job_type": "INSAR_GAMMA", "job_parameters": { "granules": [...] } } ] }
    """
    root = _pick_root(HYP3_API_URL)
    submit_url = f"{root}/jobs"

    print(f"[HyP3] base env     : {HYP3_API_URL}")
    print(f"[HyP3] root picked : {root}")
    print(f"[HyP3] POST url     : {submit_url}")
    print(f"[HyP3] jobs count   : {len(jobs_payload.get('jobs', []))}")

    h = _headers()
    r = requests.post(submit_url, headers=h, json=jobs_payload, timeout=TIMEOUT)

    print(f"[HyP3] status: {r.status_code}")
    if r.status_code >= 400:
        # דיבאג: הדפס 800 תווים ראשונים כדי להבין מה השרת מחזיר
        print("[HyP3] response (first 800 chars):")
        print(r.text[:800])
        r.raise_for_status()

    # HyP3 מחזיר JSON עם jobs
    try:
        return r.json()
    except Exception:
        print("[HyP3] ERROR: response is not JSON. First 800 chars:")
        print(r.text[:800])
        raise


# ========= דוגמה לשימוש =========
# השארתי פה דוגמה כדי שתוכל להשוות לפורמט התקין של HyP3:
# (זה בדיוק מה שהדוקס מציג) :contentReference[oaicite:1]{index=1}
def example_payload(ref_granule: str, sec_granule: str) -> dict:
    return {
        "jobs": [
            {
                "name": "satmap-insar-example",
                "job_type": "INSAR_GAMMA",
                "job_parameters": {
                    "granules": [ref_granule, sec_granule],
                },
            }
        ]
    }


if __name__ == "__main__":
    # כאן אצלך כבר יש לוגיקה שמביאה pairs ומרכיבה payload.
    # תוודא שבסוף אתה קורא:
    # resp = submit_hyp3_jobs(payload)
    # ותדפיס את resp בקצרה.

    # אם אתה מריץ ידנית ורוצה בדיקה מהירה:
    # payload = example_payload("S1A_...REF...", "S1A_...SEC...")
    # resp = submit_hyp3_jobs(payload)
    # print(json.dumps(resp, indent=2)[:2000])
    print("OK: submit_hyp3.py loaded. Hook submit_hyp3_jobs(payload) into your pipeline.")
