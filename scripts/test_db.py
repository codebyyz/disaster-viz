import asyncio
from backend import db


async def main():
    print("db.py 导入成功")
    print("DATABASE_URL =", db.DATABASE_URL)

    # 1. 初始化连接池 + 建表
    await db.init_pool()
    print("连接池初始化 + 建表: OK")

    # 2. upsert 一条测试数据
    test = [{
        "id": "test-001",
        "magnitude": 5.5,
        "place": "test place",
        "time": 1700000000000,
        "lon": 120.0,
        "lat": 30.0,
        "depth": 10.0,
    }]
    n = await db.upsert_earthquakes(test)
    print(f"upsert 写库: {n} 条")

    # 3. 读回验证
    rows = await db.fetch_earthquakes(limit=10, min_magnitude=0, max_magnitude=None, days=None)
    print(f"fetch 读回: {len(rows)} 条, 第一条 = {rows[0] if rows else 'empty'}")


asyncio.run(main())
