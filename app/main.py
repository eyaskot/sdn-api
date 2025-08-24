from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx, csv, io

DATA_URL = "https://data.opensanctions.org/datasets/20250806/us_sdn/targets.simple.csv"

app = FastAPI(title="SDN API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/getsdn")
async def getsdn(name: str = Query(..., min_length=2)):
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(DATA_URL)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch SDN data")
        content = r.content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    q = name.lower()
    rows = []
    for row in reader:
        if q in (row.get("name","").lower()):
            rows.append(row)
            if len(rows) >= 100:
                break
    return {"count": len(rows), "results": rows}
