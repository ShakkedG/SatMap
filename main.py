from __future__ import annotations
import os
from datetime import datetime

import psycopg
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="SatMap API")

DB_URL = os.getenv("SUPABASE_DB_URL", "")
API_KEY = os.getenv("SATMAP_API_KEY", "")

def db():
    if not DB_URL:
        raise HTTPException(500, "SUPABASE_DB_URL is not set")
    return psycopg.connect(DB_URL)

def require_key(x_api_key: str | None):
    if not API_KEY:
        raise HTTPException(500, "SATMAP_API_KEY is not set")
    if x_api_key != API_KEY:
        raise HTTPException(401, "Bad API key")

@app.get("/health")
def health():
    with db() as con:
        con.execute("select 1")
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.get("/runs/latest")
def runs_latest():
    with db() as con:
        row = con.execute("select value from publish_state where key='latest'").fetchone()
    return row[0] if row else {"version": None}

class SceneIn(BaseModel):
    granule_id: str
    start_time: str | None = None
    direction: str | None = None
    relative_orbit: int | None = None
    platform: str | None = None
    aoi_tag: str = "pilot"

@app.post("/scenes/upsert")
def scenes_upsert(payload: SceneIn, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    with db() as con:
        con.execute(
            """
            insert into scenes(granule_id, start_time, direction, relative_orbit, platform, aoi_tag, status)
            values (%s,%s,%s,%s,%s,%s,'new')
            on conflict (granule_id) do update set
              start_time=excluded.start_time,
              direction=excluded.direction,
              relative_orbit=excluded.relative_orbit,
              platform=excluded.platform,
              aoi_tag=excluded.aoi_tag
            """,
            (
                payload.granule_id,
                payload.start_time,
                payload.direction,
                payload.relative_orbit,
                payload.platform,
                payload.aoi_tag,
            ),
        )
        con.commit()
    return {"ok": True, "granule_id": payload.granule_id}
