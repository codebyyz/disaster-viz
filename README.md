# disaster-viz

多灾种灾害风险可视化平台（迭代中）。

当前为**第一版**：接入 USGS 地震数据，后端提供 API，前端在地图上按震级可视化。

## 效果

浏览器打开后，世界地图上按震级着色显示最近的地震点，点击圆点可查看详情（震级 / 地点 / 深度 / 时间）。

- 圆点大小 / 颜色随震级变化
  - `M < 3` 浅黄 · `M 3-5` 橙 · `M 5-6` 深橙 · `M 6+` 红
- 顶部可按**时间窗口**（24h / 7d / 30d / 90d）和**最小震级**筛选，筛选参数直接透传给 USGS
- 右侧实时统计：当前数据集中的最强震、平均震源深度

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + FastAPI + httpx + psycopg |
| 前端 | React 19 + Vite + Leaflet / react-leaflet |
| 数据 | USGS Earthquake API（免注册）+ PostgreSQL / PostGIS |
| 容器 | Docker 多阶段构建 + docker compose（双服务：app + db） |

**架构为「数据源 → 后端 → 地图」**。第二版接入 NASA FIRMS 野火数据时，只需替换 / 新增一个 adapter，后端接口与前端地图无需改动。地震数据已落 PostGIS，支持空间距离查询（`ST_Distance` / `ST_DWithin`）。

## 目录结构

```
disaster-viz/
├── backend/
│   ├── main.py             # FastAPI 应用：/ /health /earthquakes /sync + 静态挂载
│   ├── db.py               # PostgreSQL/PostGIS 数据访问层（连接池 + 建表 + upsert + 查询）
│   └── web.py              # 前端构建产物路径（DIST_DIR）
├── frontend/               # React 前端
│   ├── src/
│   │   ├── App.jsx         # 地图 + 筛选栏（核心）
│   │   ├── App.css         # 布局与样式
│   │   └── index.css       # 全局基础样式
│   └── vite.config.js      # dev server 把 /earthquakes 代理到 :8000
├── scripts/
│   ├── sync.sh             # 把改动从 Windows 工作区同步到 WSL
│   ├── dev_restart.sh      # 重启本地后端 + 冒烟
│   ├── smoke_test.py       # 全链路测试（健康 / 数据 / 筛选）
│   └── net_check.py        # 外网依赖可达性诊断
├── Dockerfile              # 两阶段构建：Node 构建前端 → Python 运行
├── docker-compose.yml
└── requirements.txt
```

## 启动方式

### 方式 A：Docker（推荐，一条命令）

```bash
cd ~/disaster-viz
docker compose up --build
```

浏览器打开 **http://localhost:8000** —— 前端页面和 API 在同一个端口。

停止：`Ctrl+C`，或 `docker compose down`。

### 方式 B：本地开发（热更新）

需要两个终端。

终端 1（后端，端口 8000）：

```bash
cd ~/disaster-viz
source venv/bin/activate
uvicorn backend.main:app --reload
```

终端 2（前端，端口 5173）：

```bash
cd ~/disaster-viz/frontend
npm run dev
```

浏览器打开 `http://localhost:5173`。前端请求 `/earthquakes` 由 Vite 代理到 `:8000`，所以**不需要 CORS，也不需要改代码**。

### 方式 C：单端口跑构建产物（不起 Docker）

```bash
cd ~/disaster-viz/frontend && npm run build && cd ..
source venv/bin/activate && uvicorn backend.main:app --port 8000
```

打开 `http://localhost:8000`。

## API

### `GET /`

前端已构建时返回页面；未构建时返回服务状态。

### `GET /health`

存活探测，给 Docker healthcheck 用。

```json
{ "status": "healthy" }
```

### `GET /earthquakes`

| 参数 | 默认 | 说明 |
|------|------|------|
| `limit` | 100 | 返回条数（1–20000） |
| `min_magnitude` | 2.5 | 最小震级 |
| `max_magnitude` | 无 | 最大震级 |
| `days` | 无 | 只取最近 N 天（1–365） |

返回：

```json
{
  "count": 100,
  "earthquakes": [
    {
      "id": "us7000tj37",
      "magnitude": 4.7,
      "place": "54 km NNW of Ende, Indonesia",
      "time": 1790048185949,
      "lon": 121.4677,
      "lat": -8.3909,
      "depth": 10
    }
  ]
}
```

> W4 起，`/earthquakes` 优先读数据库（字段 `source` = `db`）；数据库为空或不可达时回退到 USGS 实时源（`source` = `usgs` / `usgs-fallback`），保证 API 可用性。

### `POST /sync`

手动触发一次数据落库：从 USGS 拉近 30 天数据写入 PostGIS。

| 参数 | 默认 | 说明 |
|------|------|------|
| `limit` | 200 | 拉取条数（1–20000） |
| `min_magnitude` | 2.5 | 最小震级 |

```bash
curl -X POST "http://localhost:8000/sync?limit=100&min_magnitude=2.5"
```

返回 `{"fetched": 100, "written": 100}`。之后 `/earthquakes` 就命中数据库。

交互式文档：`http://localhost:8000/docs`

## 路线图

- [x] **W1** FastAPI 接入 USGS，浏览器可见 JSON
- [x] **W2** React + Leaflet 地图打点
- [x] **W3** 交互完善（时间窗口 / 震级筛选 / 详情链接）+ Docker 化
  - 容器已实跑验证（2026-10-24）：镜像 220 MB，healthcheck healthy，非 root 用户，全链路 4/4 通过
- [x] **W4** PostgreSQL / PostGIS 落库 + 文档
  - 已实跑验证（2026-10-26）：双容器（app + db），POST /sync 拉 100 条写库，/earthquakes 命中 DB（source=db），ST_Distance 空间查询通过
- [ ] 第二版：接入 NASA FIRMS 野火数据
- [ ] 第三版：北欧 / 加拿大区域多灾种数据（雪崩 / 冻土）

## 已知问题

### 1. WSL 里地图底图可能加载不出来

OSM 瓦片域名在 WSL 内被 DNS 解析到错误 IP（连 Facebook 的 IPv6 段），表现为地图灰底、没有任何瓦片。后端接口不受影响（USGS 直连正常）。

诊断：

```bash
source venv/bin/activate && python scripts/net_check.py
```

绕行方案（任选）：

- **在 Windows 浏览器里打开页面**，改在 Windows 侧验证瓦片；
- 给 WSL 配可用的 DNS（`/etc/wsl.conf` 中 `generateResolvConf=false` + 自定义 nameserver），或用 VPN 的 TUN 模式；
- 换用离线底图或自建瓦片服务（长期方案，但超出第一版范围）。

### 2. Docker 镜像拉取需要镜像加速

Docker Hub 直连超时。`~/.docker/daemon.json` 里配置了 `registry-mirrors`（顺序：`docker.1ms.run` → `DaoCloud` → `dockerproxy.net`）。

实测结论（2026-10-26）：**`docker.1ms.run` 对 postgis 等冷门镜像有缓存，是唯一能拉到的源**；DaoCloud 对 postgis 无缓存会卡死；`dockerproxy.net` 直连超时。

关键镜像 tag 记录：`postgis/postgis:16-3.4`（853 MB）可通过 `docker.1ms.run/postgis/postgis:16-3.4` 拉到，再打本地 tag 成标准名供 compose 使用。

### 3. Docker 数据目录仍在 C 盘

Docker Desktop 装在 `D:\Docker`，但镜像/容器数据（`docker_data.vhdx`）默认在 `C:\Users\Chen\AppData\Local\Docker\wsl\disk\`，迁移到 D 盘失败（`D:\` 根目录 ACL 不允许普通用户写入）。

修复方法（管理员 PowerShell）：

```powershell
icacls "D:\DockerData" /grant "DESKTOP-PC9A1Q2\Chen YunZhuo:(OI)(CI)F"
```

然后在 Docker Desktop → Resources → Advanced 把 Disk image location 设为 `D:\DockerData`。

## 开发备注

- GitHub 推送使用 Personal Access Token（不认密码）。
- 国内网络下 npm registry 建议指向镜像（本项目使用 `registry.npmmirror.com`）。
- 改完代码后如需同步 Windows 工作区 → WSL，执行 `bash scripts/sync.sh`。
