import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
import httpx, csv, io, time, logging

SDN_CSV_URL = os.environ.get(
     "SDN_CSV_URL", 
     "https://data.opensanctions.org/datasets/20250806/us_ofac_sdn/targets.simple.csv",
)
CACHE_TTL_SECONDS = int(os.environ.get("SDN_CACHE_TTL", "3600"))
RESULT_LIMIT = int(os.environ.get("SDN_RESULT_LIMIT", "200"))

class SdnItem(BaseModel):
    """
    SDN item mapped from CSV with headers:
    "id","schema","name","aliases","birth_date","countries","addresses","identifiers","sanctions","phones","emails","dataset","first_seen","last_seen","last_change"
    """
    id: Optional[str] = None
    name: Optional[str] = None
    birth_date: Optional[str] = None
    countries: Optional[str] = None
    addresses: Optional[str] = None
    sanctions: Optional[str] = None
    dataset: Optional[str] = None
    
    class Config:
        populate_by_name = True
        extra = "ignore"

class SdnResponse(BaseModel):
    count: int
    results: List[SdnItem]

class HealthzResponse(BaseModel):
    status: str
    rows: Optional[int] = None
    source: str
    detail: Optional[str] = None

app = FastAPI(title="Aurelia SDN API", version="1.0.0", description="SDN Sanctions List API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sdn-api")

class _Cache:
    rows: Optional[List[dict]] = None
    ts: float = 0.0
cache = _Cache()

async def _fetch_csv_rows() -> List[dict]:
    now = time.time()
    if cache.rows is not None and (now - cache.ts) < CACHE_TTL_SECONDS:
        return cache.rows

    headers = {
        "User-Agent": "AureliaBank-AML/1.0 (+sdn-api)",
        "Accept": "text/csv,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(SDN_CSV_URL, headers=headers)
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        log.exception("Failed to fetch SDN CSV")
        raise HTTPException(status_code=503, detail=f"Failed to fetch SDN data: {e}")

    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except Exception as e:
        log.exception("Failed to parse SDN CSV")
        raise HTTPException(status_code=500, detail=f"Failed to parse SDN CSV: {e}")

    cache.rows = rows
    cache.ts = now
    log.info("Loaded %d SDN rows (cache ttl=%ds)", len(rows), CACHE_TTL_SECONDS)
    return rows

@app.get("/healthz", response_model=HealthzResponse)
async def healthz():
    try:
        rows = await _fetch_csv_rows()
        return HealthzResponse(status="ok", rows=len(rows), source=SDN_CSV_URL)
    except HTTPException as e:
        return HealthzResponse(status="degraded", detail=str(e.detail), source=SDN_CSV_URL)

@app.get("/getsdn", response_model=SdnResponse)
async def getsdn(name: str = Query(..., min_length=2, description="Case-insensitive contains match on SDN name")):
    rows = await _fetch_csv_rows()
    q = name.lower().strip()
    matches = [r for r in rows if q in (r.get("name") or "").lower()]
    items = [SdnItem.model_validate(r) for r in matches[:RESULT_LIMIT]]
    return SdnResponse(count=len(matches), results=items)
