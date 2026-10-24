# W3 — 交互完善 + Docker 化

> 2026-10-24 · disaster-viz

## 目标回顾

W3 的原始定义：**交互（弹窗 / 筛色）+ 写进 Docker，`docker compose up` 一键起。**
验收标准只有一条：**能不能演示。**

## 这次做了什么

### 1. 后端结构重整（为 W4 铺路）

| 变化 | 原因 |
|------|------|
| `main.py` → `backend/main.py` | W4 要加 `db.py`、`adapters/`，根目录平铺会失控；提前分目录，后续 move 成本为零 |
| 新增 `GET /health` | Docker healthcheck 需要便宜、无外部依赖的探测点。不能拿 `/earthquakes` 做探测——它依赖 USGS，外网抖动会让容器被误判为不健康 |
| 新增 `days` / `max_magnitude` 参数 | 筛选在**数据源端**完成。USGS 支持 `starttime=now-7days`，让它筛比拉全量回来再筛省掉几个数量级的流量 |
| 抽 `normalize()` | 前端字段、落库字段、将来 adapters 的字段必须同源，只写一次 |
| 新增 `backend/web.py`（`DIST_DIR`） | 前端产物路径集中管理 |

### 2. 前端交互

- **时间窗口**：24h / 7d / 30d / 90d
- **最小震级**：全部 / M2.5+ / M4.5+ / M6+
- 顶部统计条：数据集内最强震（震级 + 地点）、平均震源深度
- 弹窗内加「查看 USGS 详情」外链
- 选中点描边加粗
- **请求可取消**：切筛选时 `AbortController` 打断上一个请求，避免旧响应覆盖新结果（经典的 race condition）

### 3. 开发体验：前后端同源

原来：前端硬编码 `http://localhost:8000`，靠 CORS 放行。
现在：前端统一用相对路径 `/earthquakes`，开发时由 **Vite proxy** 转发到 `:8000`。

好处是开发时和 Docker 里的行为完全一致（都是同源），不用「开发能跑、进容器就 404」这种坑。

### 4. Docker 化

两阶段构建：

```
node:22-alpine        → npm ci + vite build
python:3.12-slim      → venv + backend/ + dist/
```

细节选择：

| 决定 | 理由 |
|------|------|
| 前端在容器内构建 | 产物和源码强一致，谁 clone 都能复现；不依赖本地 `dist/` 是否最新 |
| `VITE_API_BASE=""` | 同源，无 CORS，不写死主机名，部署到云上也不用改 |
| 非 root 用户 `appuser` | 容器被攻破时的最小权限 |
| healthcheck 用 `python -c urllib` | slim 镜像没 curl，为探测再装 curl 多几十 MB |
| 单服务 compose | 现在只有一个容器，拆多个是假微服务。W4 加 Postgres 才是 compose 真正的价值 |

### 5. 踩坑记录（值得记住）

**静态站点挂载在 Starlette 里很坑。**

- `app.mount("", StaticFiles(html=True))` → 路由变成 `/frontend`，无法命中
- `app.mount("/", ...)` → 吃掉 `GET /` 的 API 路由，返回目录列表
- 正解：`GET /` 用 `FileResponse(index.html)`，静态资源 `app.mount("/assets", ...)`

另外 `html=True` 的 fallback 会让 `/earthquakes` 之类未匹配路径落到静态目录，掩盖真实 404 —— 所以只挂子路径。

**WSL 里的网络是独立的。**
`tile.openstreetmap.org` 在 WSL 内被解析到错误的 IP（31.13.x / Facebook 的 IPv6 段），直连和走代理都失败；而 `earthquake.usgs.gov` 直连正常。这不是代码问题，是 WSL DNS 的问题，后端不受影响。

## 验证结果

```
$ python scripts/smoke_test.py
[PASS] GET /health — {"status":"healthy"}
[PASS] GET /earthquakes 返回数据 — count=5
[PASS] min_magnitude 过滤生效 — magnitudes=[5.1, 5, 5.3, 5.8, 5.7]
3/3 passed
```

```
$ python scripts/probe_routes.py
[200] GET /                  (text/html)   -> <!doctype html> ...
[200] GET /assets/index-*.js (text/javascript)
[200] GET /earthquakes       (application/json)
[404] GET /nonexistent       (application/json)
```

前端 `npm run build` 通过，`oxlint`：0 warnings / 0 errors。

## 未完成 / 下一步

- [ ] **Docker 实跑验证**：镜像和 compose 文件已写好，但本机 WSL 还没装 Docker。安装后需验证 `docker compose up` 能起、healthcheck 变 healthy
- [ ] 地图底图在 WSL 内不可见（公网 DNS 问题），演示建议在 Windows 浏览器做
- [ ] W4：PostgreSQL/PostGIS 落库，compose 变成 app + db 两服务

## 给下一个「我」的提示

- 后端起服务：`bash scripts/dev_restart.sh`
- 改完 Windows 工作区的代码要先 `bash scripts/sync.sh`
- 接口文档：`http://localhost:8000/docs`
