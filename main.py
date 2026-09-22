from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Disaster Viz API")

# --- CORS ---
# 前端跑在 http://localhost:5173（Vite 默认端口），后端在 8000。
# 浏览器出于同源策略会拦截跨端口请求，必须显式允许。
# 开发阶段允许 localhost 各端口；上线后应改成具体域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


@app.get("/")
def root():
    return {"status": "ok", "project": "disaster-viz"}


@app.get("/earthquakes")
async def get_earthquakes(limit: int = 100, min_magnitude: float = 2.5):
    params = {
        "format": "geojson",
        "limit": limit,
        "minmagnitude": min_magnitude,
        "orderby": "time",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(USGS_URL, params=params)
        resp.raise_for_status()
    data = resp.json()

    features = [
        {
            "id": f["id"],
            "magnitude": f["properties"]["mag"],
            "place": f["properties"]["place"],
            "time": f["properties"]["time"],
            "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1],
            "depth": f["geometry"]["coordinates"][2],
        }
        for f in data["features"]
    ]
    return {"count": len(features), "earthquakes": features}
