"""disaster-viz 后端入口。

本地开发（前后端分离，热更新）：
    uvicorn backend.main:app --reload      # :8000
    cd frontend && npm run dev             # :5173

生产 / Docker（单端口）：
    前端已构建到 frontend/dist 时，后端会把它挂到根路径，只需访问 :8000
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

from backend.web import DIST_DIR

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


def normalize(f: dict) -> dict:
    """把 USGS GeoJSON feature 转成前端用的扁平结构。

    单独抽成函数的原因：W3 加筛选后前端要复用字段，W4 落库时
    也要用同一套字段名，避免两处各写一遍解析逻辑。
    """
    props = f.get("properties") or {}
    coords = (f.get("geometry") or {}).get("coordinates") or [None, None, None]
    return {
        "id": f["id"],
        "magnitude": props.get("mag"),
        "place": props.get("place"),
        "time": props.get("time"),
        "lon": coords[0],
        "lat": coords[1],
        "depth": coords[2],
    }


@app.get("/")
async def root():
    """前端已构建就返回页面，否则返回 API 状态（Vite dev server 开发模式）。"""
    if FRONTEND_READY:
        return FileResponse(DIST_DIR / "index.html")
    return {"status": "ok", "project": "disaster-viz"}


@app.get("/health")
def health():
    """给 Docker healthcheck / 容器编排用的存活探测。"""
    return {"status": "healthy"}


@app.get("/earthquakes")
async def get_earthquakes(
    limit: int = Query(100, ge=1, le=20000),
    min_magnitude: float = Query(2.5, ge=-1, le=10),
    max_magnitude: float | None = Query(None, ge=0, le=10),
    days: int | None = Query(None, ge=1, le=365, description="只取最近 N 天"),
):
    """从 USGS 拉取地震事件。

    参数直接透传给 USGS，由数据源端过滤 —— 不要拉全量到本地再筛，
    那会把网络和内存成本放大几个数量级。
    """
    params = {
        "format": "geojson",
        "limit": limit,
        "minmagnitude": min_magnitude,
        "orderby": "time",
    }
    if max_magnitude is not None:
        params["maxmagnitude"] = max_magnitude
    if days is not None:
        params["starttime"] = f"now-{days}days"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(USGS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    features = [normalize(f) for f in data.get("features", [])]
    return {"count": len(features), "earthquakes": features}


# 静态资源挂载：只挂子路径，不占用根路径。
#
# 踩过的坑：把 StaticFiles(html=True) 挂到 "/" 时，Starlette 的 Mount
# 会把 GET / 也吞掉，导致根路径返回目录列表而不是 index.html；
# 而挂到 "" 又会被当成 "/frontend"。
# 现在做法是：/ 用 FileResponse 拍返回 index.html，其余静态文件走 /assets。
# 开发环境下 dist 可能不存在，此时只提供 API（前端走 Vite dev server）。
FRONTEND_READY = (DIST_DIR / "index.html").exists()
if FRONTEND_READY:
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")
