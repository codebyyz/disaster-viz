"""PostgreSQL/PostGIS 数据访问层。

W4 的目标：把 normalize() 之后的扁平字段落到 PostGIS 里，让平台从
「实时回源 USGS」升级为「有历史数据积累 + 能做空间查询」。

为什么用 psycopg（而非 asyncpg + 手写 SQL）？
  psycopg3 是现役标准驱动，跟后续想接 SQLAlchemy 的路线兼容；
  同时 SQL 仍由我们显式写出，能真正理解 PostGIS 语法。
  这里用的是 psycopg 的 async 接口（psycopg.AsyncConnection），
  与 FastAPI / httpx 的 async 栈保持一致，不阻塞事件循环。

连接串来源：
  优先读环境变量 DATABASE_URL（容器内由 compose 注入），
  本地裸跑时回退到默认的 localhost:5432 的 disaster_viz 库。
"""
from __future__ import annotations

import os

import psycopg
from psycopg_pool import AsyncConnectionPool

# 默认连接串 —— 本地开发 & compose 内都能用（compose 里 DATABASE_URL 覆盖掉 host）。
DEFAULT_DATABASE_URL = (
    "postgresql://disaster:disaster@localhost:5432/disaster_viz"
)
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

# 连接池：避免每次请求都新建连接。min_size=0 表示空闲时一个连接都不占，
# 冷启动不拖累没有数据库场景下的 API（详见 get_earthquakes 的兜底逻辑）。
pool: AsyncConnectionPool | None = None

# 建表语句（幂等，可反复执行）。
# geom 用 PostGIS 的 geography 类型（4326 经纬度），
# 方便后面做 ST_DWithin 之类按米算距离的空间查询。
SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS earthquakes (
    id         TEXT PRIMARY KEY,
    magnitude  DOUBLE PRECISION,
    place      TEXT,
    time       BIGINT,
    lon        DOUBLE PRECISION,
    lat        DOUBLE PRECISION,
    depth      DOUBLE PRECISION,
    geom       GEOGRAPHY(Point, 4326),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_earthquakes_geom
    ON earthquakes USING GIST (geom);
"""

# 写入地震事件，主键冲突时更新（upsert）。
# 同一事件 USGS 的 id 稳定，反复 sync 不会重复插。
UPSERT_SQL = """
INSERT INTO earthquakes (id, magnitude, place, time, lon, lat, depth, geom)
VALUES (%s, %s, %s, %s, %s, %s, %s,
        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
ON CONFLICT (id) DO UPDATE SET
    magnitude  = EXCLUDED.magnitude,
    place      = EXCLUDED.place,
    time       = EXCLUDED.time,
    lon        = EXCLUDED.lon,
    lat        = EXCLUDED.lat,
    depth      = EXCLUDED.depth,
    geom       = EXCLUDED.geom,
    fetched_at = now();
"""


async def init_pool() -> AsyncConnectionPool:
    """惰性初始化连接池并建表。

    设计考量：不在模块导入时就连数据库。因为 /earthquakes 在数据库
    没起时也必须能工作（回源 USGS 兜底）。只有真正要读写时才连。
    """
    global pool
    if pool is None:
        pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=0,
            max_size=4,
            open=False,  # 手动 open，便于在 init 时跑建表语句
        )
        await pool.open()
        async with pool.connection() as conn:
            await conn.execute(SCHEMA_SQL)
    return pool


async def upsert_earthquakes(rows: list[dict]) -> int:
    """把一批 normalize() 后的字典写入数据库，返回写入条数。

    rows 里的字段与 main.normalize() 的返回值一一对应。
    """
    if not rows:
        return 0
    p = await init_pool()
    async with p.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                UPSERT_SQL,
                [
                    (
                        r["id"],
                        r["magnitude"],
                        r["place"],
                        r["time"],
                        r["lon"],
                        r["lat"],
                        r["depth"],
                        r["lon"],
                        r["lat"],
                    )
                    for r in rows
                ],
            )
        return len(rows)


async def fetch_earthquakes(
    limit: int,
    min_magnitude: float,
    max_magnitude: float | None,
    days: int | None,
) -> list[dict]:
    """从数据库读取地震事件，结构与 USGS 源返回保持一致。

    筛选逻辑在 SQL 层做（跟「别拉全量到本地再筛」是同一原则）。
    时间戳（time）是 USGS 的毫秒 epoch，days 用毫秒换算比较。
    """
    p = await init_pool()
    conditions = ["magnitude >= %(min_mag)s"]
    params: dict = {"min_mag": min_magnitude, "limit": limit}

    if max_magnitude is not None:
        conditions.append("magnitude <= %(max_mag)s")
        params["max_mag"] = max_magnitude

    if days is not None:
        conditions.append("time >= %(since)s")
        params["since"] = _ms_days_ago(days)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT id, magnitude, place, time, lon, lat, depth
        FROM earthquakes
        WHERE {where}
        ORDER BY time DESC
        LIMIT %(limit)s
    """

    async with p.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()

    return [
        {
            "id": r[0],
            "magnitude": r[1],
            "place": r[2],
            "time": r[3],
            "lon": r[4],
            "lat": r[5],
            "depth": r[6],
        }
        for r in rows
    ]


def _ms_days_ago(days: int) -> int:
    """返回 N 天前的毫秒 epoch（对齐 USGS 的 time 字段单位）。"""
    import time

    return int((time.time() - days * 86400) * 1000)
