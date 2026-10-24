import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def show(label, resp, n=90):
    ct = resp.headers.get("content-type", "")
    body = resp.text.replace("\n", "")[:n]
    print(f"[{resp.status_code}] {label} ({ct.split(';')[0]}) -> {body}")


with httpx.Client(base_url=BASE, timeout=30) as c:
    show("GET /health", c.get("/health"))
    show("GET /", c.get("/"))
    show("GET /earthquakes?limit=1", c.get("/earthquakes", params={"limit": 1}))
    show("GET /nonexistent", c.get("/nonexistent"))

    r = c.get("/")
    if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
        import re

        asset = re.search(r'src="(/assets/[^"]+\.js)"', r.text)
        if asset:
            show("GET " + asset.group(1), c.get(asset.group(1)), n=60)
        else:
            print("[WARN] index.html 里没找到 /assets/*.js 引用")
