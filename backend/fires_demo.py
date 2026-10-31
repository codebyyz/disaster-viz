"""FIRMS 演示数据（无 key 时可用）。

存在的理由：拿到 MAP_KEY 前，野火 tab 是空的，页面没法演示、没法验收。
这个模块提供一小组「形状与真实响应完全一致」的样例热点，
让前端、selftest 和截图都能在没有网络/没有 key 的情况下跑通。

**这不是伪造数据冒充真实数据**：
  - 只在显式设置 FIRMS_DEMO=1 时启用
  - 响应里 source 标为 "firms-demo"，前端会明确提示「演示数据」
  - 任何真实场景（有 key）下这个模块完全不参与

样例取自真实热点记录的形态（坐标、亮温、FRP、置信度都有），
覆盖北美、澳洲、地中海、亚马逊等典型野火区，方便前端看效果。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

DEMO_ENABLED = os.environ.get("FIRMS_DEMO", "").strip().lower() in ("1", "true", "yes")

# (lat, lon, 亮温K, FRP兆瓦, 置信度, 卫星, 昼/夜)
_DEMO_POINTS = [
    (38.29, -122.46, 367.4, 42.1, "h", "NOAA-21", "D"),   # 加州
    (39.73, -121.62, 351.8, 28.6, "h", "NOAA-21", "D"),   # 加州北部
    (40.94, -124.10, 335.2, 15.3, "n", "NOAA-20", "D"),   # 加州西北
    (-33.87, 150.91, 344.6, 21.7, "h", "NOAA-21", "D"),   # 澳洲悉尼西
    (-35.28, 149.13, 328.9, 9.4, "n", "NOAA-20", "D"),    # 澳洲堪培拉
    (38.64, 22.94, 358.1, 33.8, "h", "NOAA-21", "N"),     # 希腊
    (39.52, 20.86, 341.3, 18.2, "n", "NOAA-21", "N"),     # 希腊西部
    (-3.47, -62.22, 372.8, 57.9, "h", "NOAA-20", "D"),    # 亚马逊
    (-9.67, -55.68, 362.5, 44.3, "h", "NOAA-21", "D"),    # 巴西中部
    (52.13, -106.67, 318.4, 6.1, "l", "NOAA-20", "D"),    # 加拿大草原
    (55.86, -97.25, 309.7, 4.8, "l", "NOAA-21", "D"),     # 加拿大北部
    (44.98, -93.27, 315.6, 5.5, "n", "NOAA-20", "D"),     # 明尼苏达
    (31.05, 118.76, 337.9, 14.6, "n", "NOAA-21", "D"),    # 中国东部
    (42.98, 89.19, 349.2, 26.4, "h", "NOAA-21", "D"),     # 新疆
    (61.22, 73.40, 322.7, 7.9, "n", "NOAA-20", "D"),      # 西伯利亚
]

_INSTRUMENT = "VIIRS"


def demo_fires(days: int = 1) -> list[dict]:
    """生成与 firms.normalize_fire 输出结构一致的上条样例数据。

    时间戳按「最近 days 天内」均匀铺开，看起来像真实采集结果。
    """
    now = datetime.now(timezone.utc)
    fires = []
    per_day = max(1, len(_DEMO_POINTS) // max(1, days))
    for i, (lat, lon, bright, frp, conf, sat, daynight) in enumerate(_DEMO_POINTS):
        # 把点摊到 days 天内，且同一天内错开小时。
        day_offset = (i // per_day) % max(1, days)
        hour_offset = (i * 3) % 24
        ts = (now - timedelta(days=day_offset)).replace(
            hour=hour_offset, minute=(i * 7) % 60, second=0, microsecond=0
        )
        acq_date = ts.strftime("%Y-%m-%d")
        acq_time = ts.strftime("%H%M")
        fires.append(
            {
                "id": f"{lat},{lon}|{acq_date}|{sat}|{acq_time}",
                "bright_ti4": bright,
                "frp": frp,
                "confidence": conf,
                "satellite": sat,
                "instrument": _INSTRUMENT,
                "daynight": daynight,
                "time": ts.isoformat().replace("+00:00", "Z"),
                "lon": lon,
                "lat": lat,
            }
        )
    return fires
