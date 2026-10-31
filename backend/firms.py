"""NASA FIRMS 野火数据 adapter（第二版新增）。

跟 USGS 那条链路的区别，正好用来练「接入需要 API key 的第三方源」：

  1. 返回 CSV 而不是 JSON —— 需要用标准库 csv 解析，不能直接 .json()。
  2. 需要 MAP_KEY —— 免费注册，发到邮箱，存在环境变量 FIRMS_MAP_KEY。
  3. URL 是「路径式」而非 query 参数 —— 参数直接拼进 path。

为什么单独一个模块而不是塞进 main.py？
  跟 web.py 同一思路：把「数据源特有的解析逻辑」隔离出来。
  将来加第三个源（雪崩/冻土），就是再写一个这样的 adapter，
  main.py 只负责路由和调用，不关心每个源长什么样。

FIRMS area API 约定（官方文档，务必对照）：
  GET /api/area/csv/{MAP_KEY}/{SOURCE}/{AREA_COORDINATES}/{DAY_RANGE}[/{DATE}]
    SOURCE            : VIIRS_NOAA21_NRT / VIIRS_NOAA20_NRT / MODIS_NRT 等
    AREA_COORDINATES  : "world" 或 "west,south,east,north"
    DAY_RANGE         : 1..5（最多一次查 5 天）
    DATE              : YYYY-MM-DD，可选；不给则返回最近数据

CSV 列（会随 sensor 略有差异，核心列稳定）：
  latitude, longitude, brightness, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, bright_ti4, frp, daynight
"""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime

import httpx

# FIRMS area API 的路径式模板。
# 注意：不是 ?MAP_KEY=... 的 query 形式，而是拼进 URL path 里。
FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# 可选传感器。VIIRS NOAA-21 NRT 是目前主力产品（Suomi NPP 自 2026-11-02 停供，
# FIRMS 官方建议转 NOAA-20 / NOAA-21）。SOURCE 必须带 _NRT 后缀。
DEFAULT_SENSOR = "VIIRS_NOAA21_NRT"

# DAY_RANGE 上限（FIRMS 硬性约束 1..5）。
MAX_DAY_RANGE = 5

# 环境变量在模块导入时读一次够用；key 不会变。
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")


def normalize_fire(row: dict) -> dict:
    """把 FIRMS CSV 的一行转成前端用的扁平结构。

    bright_ti4 是「亮温」（开尔文），可近似当热强度看待，
    用来驱动前端圆点的颜色和大小（跟地震的 magnitude 类似）。
    frp 是 Fire Radiative Power（辐射功率，兆瓦），真正反映火强，
    但部分行可能缺，先取 bright_ti4 保证每点都有值。
    """
    # acq_date 形如 "2026-10-30"，acq_time 形如 "0745"（UTC 的 HHMM）。
    # 拼一个可排序、可显示的 ISO 时间戳（前端 new Date 直接能认）。
    acq_date = (row.get("acq_date") or "").strip()
    acq_time = ((row.get("acq_time") or "").strip()).zfill(4)
    ts = None
    if acq_date:
        try:
            ts = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").isoformat() + "Z"
        except ValueError:
            ts = acq_date  # 解析失败退化为只要日期

    lat = _to_float(row.get("latitude"))
    lon = _to_float(row.get("longitude"))

    return {
        # FIRMS 没有稳定的单行 id（不像 USGS 的 event id），
        # 用坐标+日期+卫星+时间拼一个，足够当 React key 使用。
        "id": f"{lat},{lon}|{acq_date}|{row.get('satellite')}|{acq_time}",
        "bright_ti4": _to_float(row.get("bright_ti4")),
        "frp": _to_float(row.get("frp")),
        "confidence": row.get("confidence"),
        "satellite": row.get("satellite"),
        "instrument": row.get("instrument"),
        "daynight": row.get("daynight"),
        "time": ts,
        "lon": lon,
        "lat": lat,
    }


def _to_float(v):
    """把 CSV 里的字符串安全转 float；空值返回 None。"""
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


async def fetch_fires(days: int = 1, sensor: str | None = None) -> list[dict]:
    """从 FIRMS 拉近 N 天全球热点，解析 CSV 并 normalize。

    用 httpx 直接拿文本（csv 模块需要文本流），而不是 resp.json()。
    days 会被 clamp 到 1..5（FIRMS 的 DAY_RANGE 上限）。
    """
    if not FIRMS_MAP_KEY:
        raise RuntimeError(
            "缺少 FIRMS_MAP_KEY 环境变量。"
            "去 https://firms.modaps.eosdis.nasa.gov/api/map_key 免费注册，"
            "把 key 填进 .env（参考 .env.example）。"
        )

    sensor = sensor or DEFAULT_SENSOR
    day_range = max(1, min(int(days), MAX_DAY_RANGE))

    # 路径式 URL：/area/csv/{KEY}/{SOURCE}/{AREA}/{DAY_RANGE}
    url = f"{FIRMS_AREA_URL}/{FIRMS_MAP_KEY}/{sensor}/world/{day_range}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    return [normalize_fire(row) for row in reader]
