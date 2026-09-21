from fastapi import FastAPI
import httpx

app = FastAPI(title="Disaster Viz API")

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
