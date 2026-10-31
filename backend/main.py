"""disaster-viz 后端入口。

本地开发（前后端分离，热更新）：
    uvicorn backend.main:app --reload      # :8000
    cd frontend && npm run dev             # :5173

生产 / Docker（单端口）：
    前端已构建到 frontend/dist 时，后端会把它挂到根路径，只需访问 :8000
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

from backend import db
from backend import firms
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


async def _fetch_from_usgs(params: dict) -> list[dict]:
    """从 USGS 拉取并 normalize，供 /earthquakes 和 /sync 复用。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(USGS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return [normalize(f) for f in data.get("features", [])]


@app.get("/earthquakes")
async def get_earthquakes(
    limit: int = Query(100, ge=1, le=20000),
    min_magnitude: float = Query(2.5, ge=-1, le=10),
    max_magnitude: float | None = Query(None, ge=0, le=10),
    days: int | None = Query(None, ge=1, le=365, description="只取最近 N 天"),
):
    """读取地震事件：数据库优先，回源 USGS 兜底。

    W4 起，数据走 PostGIS。逻辑如下：
      1) 查数据库；若有数据直接用（命中即返回，并标注 source="db"）。
      2) 数据库为空（首次启动/没触发过 sync）→ 回源 USGS，
         并顺手把结果写库（此后 DB 不再空），返回 source="usgs"。
      3) 两者都失败 → 抛错，不吞异常。
    """
    try:
        rows = await db.fetch_earthquakes(limit, min_magnitude, max_magnitude, days)
        if rows:
            return {"count": len(rows), "source": "db", "earthquakes": rows}

        # DB 命中但为空（可能是刚建库，或筛选条件把数据筛没了）。
        # 回源 USGS 拿一份，并顺手写库。
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

        features = await _fetch_from_usgs(params)
        await db.upsert_earthquakes(features)
        return {"count": len(features), "source": "usgs", "earthquakes": features}
    except Exception as exc:
        # 数据库不可达时，退化为纯回源模式，保证 API 可用。
        # （W4 的容错设计：DB 是增强，不是单点依赖。）
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
        features = await _fetch_from_usgs(params)
        return {"count": len(features), "source": "usgs-fallback", "earthquakes": features}


@app.get("/fires")
async def get_fires(
    days: int = Query(1, ge=1, le=5, description="最近 N 天（FIRMS 上限 5 天）"),
    sensor: str | None = Query(None, description="传感器，如 VIIRS_NOAA21_NRT"),
):
    """读取野火热点：从 NASA FIRMS 拉 CSV 并 normalize。

    第二版新增的第二个数据源。与 /earthquakes 不同点：
      - 需要 MAP_KEY（FIRMS_MAP_KEY 环境变量）
      - 返回 CSV，在 firms.py 里解析
      - 暂不落库（数据量大、变化快，落库留给第三版统一设计 schema）
    """
    try:
        fires = await firms.fetch_fires(days=days, sensor=sensor)
        return {"count": len(fires), "source": "firms", "fires": fires}
    except RuntimeError as exc:
        # 配置问题（缺 MAP_KEY）→ 400。前端据此提示「去填 key」。
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPError as exc:
        # 上游 FIRMS 不可达 / 报错 → 502。跟 400 区分开，
        # 便于前端和排障时判断是「配置没填」还是「网络/上游挂了」。
        raise HTTPException(
            status_code=502, detail=f"NASA FIRMS 请求失败：{exc}"
        )


@app.post("/sync")
async def sync_earthquakes(
    limit: int = Query(200, ge=1, le=20000),
    min_magnitude: float = Query(2.5, ge=-1, le=10),
):
    """手动触发一次数据落库：拉 USGS 近 30 天数据写进 PostGIS。

    为什么手动而不是定时：W4 先把「写库」这条链路跑通、可验证；
    定时调度（cron/APScheduler）是之后的进阶，避免一次引入太多面。
    """
    params = {
        "format": "geojson",
        "limit": limit,
        "minmagnitude": min_magnitude,
        "orderby": "time",
        "starttime": "now-30days",
    }
    features = await _fetch_from_usgs(params)
    written = await db.upsert_earthquakes(features)
    return {"fetched": len(features), "written": written}


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
