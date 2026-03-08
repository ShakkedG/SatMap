-- SatMap InSAR Processing Catalog and Job Tracking

-- 1) PostGIS
create extension if not exists postgis;

-- 2) Scenes discovered from catalog (ASF)
create table if not exists scenes (
  granule_id text primary key,
  start_time timestamptz,
  stop_time timestamptz,
  direction text,              -- ASCENDING / DESCENDING
  relative_orbit int,
  platform text,               -- S1A/S1C וכו'
  aoi_tag text default 'pilot',
  status text default 'new',   -- new/paired/processed/failed
  meta jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists scenes_time_idx on scenes (start_time);
create index if not exists scenes_status_idx on scenes (status);

-- 3) SBAS pairs to submit to HyP3
create table if not exists pairs (
  pair_key text primary key,          -- e.g. ref__sec
  ref_granule_id text not null references scenes(granule_id),
  sec_granule_id text not null references scenes(granule_id),
  status text default 'new',          -- new/submitted/done/failed
  created_at timestamptz default now()
);

create index if not exists pairs_status_idx on pairs (status);

-- 4) HyP3 jobs + results
create table if not exists hyp3_jobs (
  job_id text primary key,
  pair_key text not null references pairs(pair_key),
  product_type text,                  -- insar/burst_insar וכו'
  status text,                        -- running/succeeded/failed
  submitted_at timestamptz default now(),
  updated_at timestamptz default now(),
  result_meta jsonb default '{}'::jsonb
);

create index if not exists hyp3_jobs_status_idx on hyp3_jobs (status);

-- 5) Publish state pointer for the client
create table if not exists publish_state (
  key text primary key,
  value jsonb
);

insert into publish_state(key, value)
values ('latest', jsonb_build_object('version', null))
on conflict (key) do nothing;
