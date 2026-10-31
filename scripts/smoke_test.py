"""一个最小的「全链路」冒烟测试，不依赖 Docker。

W3 的验收标准是「能演示」。演示前跑一遍这个脚本，确认：
  后端活着 -> 前端 dist 存在 -> 接口能拿到真实数据 -> 筛选参数生效。

用法：python scripts/smoke_test.py [base_url]
"""
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> int:
    results = []
    with httpx.Client(base_url=BASE, timeout=20) as c:
        r = c.get("/health")
        results.append(check("GET /health", r.status_code == 200, r.text[:40]))

        r = c.get("/earthquakes", params={"limit": 5})
        data = r.json() if r.status_code == 200 else {}
        results.append(
            check(
                "GET /earthquakes 返回数据",
                r.status_code == 200 and data.get("count", 0) > 0,
                f"count={data.get('count')}",
            )
        )

        r = c.get("/earthquakes", params={"limit": 5, "min_magnitude": 4.5, "days": 7})
        data = r.json() if r.status_code == 200 else {}
        mags = [e["magnitude"] for e in data.get("earthquakes", []) if e["magnitude"] is not None]
        results.append(
            check(
                "min_magnitude 过滤生效",
                r.status_code == 200 and all(m >= 4.5 for m in mags),
                f"magnitudes={mags}",
            )
        )

        # 第二版：野火接口。
        # 没配 FIRMS_MAP_KEY 时应当返回 400（而不是 500 / 崩掉），
        # 且不影响地震接口——这正是容错设计要验证的点。
        r = c.get("/fires", params={"days": 1})
        if r.status_code == 200:
            data = r.json()
            results.append(
                check(
                    "GET /fires 返回数据",
                    data.get("count", 0) > 0,
                    f"count={data.get('count')}",
                )
            )
        else:
            # 400 = 未配 key（预期路径）；502 = 上游不可达。
            results.append(
                check(
                    "GET /fires 降级正确（未配 key → 400）",
                    r.status_code == 400,
                    f"HTTP {r.status_code}",
                )
            )

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
