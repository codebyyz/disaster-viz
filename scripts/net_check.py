"""WSL 网络诊断：判断哪些外部依赖通、哪些不通。

用途：地图瓦片（OSM）在 WSL 里直连被劫持到错误 IP 时会一直卡住。
这个脚本只读网络状态，不改任何配置。
"""
import os
import socket
import time

import httpx

TARGETS = {
    "USGS (后端数据源)": "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1",
    "OSM 瓦片 (地图底图)": "https://tile.openstreetmap.org/2/1/1.png",
    "CartoDB 深色瓦片 (备选)": "https://a.basemaps.cartocdn.com/dark_all/2/1/1.png",
}

PROXY = os.environ.get("HTTPS_PROXY") or "http://172.26.176.1:9674"


def resolve(host: str) -> str:
    try:
        ips = {ai[4][0] for ai in socket.getaddrinfo(host, 443, socket.AF_INET)}
        return ", ".join(sorted(ips))
    except Exception as e:  # noqa: BLE001
        return f"解析失败: {e}"


def probe(url: str, proxy: str | None) -> str:
    start = time.time()
    try:
        with httpx.Client(proxy=proxy, timeout=8.0, verify=False) as c:
            r = c.get(url)
        return f"{r.status_code}  {time.time() - start:.2f}s"
    except Exception as e:  # noqa: BLE001
        return f"FAIL  {type(e).__name__}:{time.time() - start:.2f}s"


if __name__ == "__main__":
    for name, url in TARGETS.items():
        host = url.split("/")[2]
        print(f"== {name}")
        print(f"   DNS   -> {resolve(host)}")
        print(f"   直连  -> {probe(url, None)}")
        print(f"   代理  -> {probe(url, PROXY)}")
