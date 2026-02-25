import json, requests

URL = "https://www.govmap.gov.il/api/layers-catalog/entitiesByPoint"

with open("pipeline/govmap_entitiesByPoint_payload.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

r = requests.post(URL, json=payload, timeout=60)
print("status:", r.status_code)
r.raise_for_status()

data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2)[:20000])  # מדפיס עד 20k תווים
