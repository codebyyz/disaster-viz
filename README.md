# disaster-viz

多灾种灾害风险可视化平台（迭代中）。

当前为**第一版**：接入 USGS 地震数据，后端提供 API，前端在地图上按震级可视化。

## 效果

浏览器打开后，世界地图上按震级着色显示最近的地震点，点击圆点可查看详情（震级 / 地点 / 深度 / 时间）。

- 圆点大小 / 颜色随震级变化
  - `M < 3` 浅黄 · `M 3-5` 橙 · `M 5-6` 深橙 · `M 6+` 红

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 + FastAPI + httpx |
| 前端 | React 19 + Vite + Leaflet / react-leaflet |
| 数据 | USGS Earthquake API（免注册） |

**架构为「数据源 → 后端 → 地图」**。第二版接入 NASA FIRMS 野火数据时，只需替换 / 新增一个 adapter，后端接口与前端地图无需改动。

## 目录结构

```
disaster-viz/
├── main.py                 # FastAPI 服务：/ 和 /earthquakes
├── requirements.txt        # Python 依赖
├── frontend/               # React 前端
│   ├── src/
│   │   ├── App.jsx         # 地图组件（核心）
│   │   ├── App.css         # 布局与样式
│   │   └── index.css       # 全局基础样式
│   └── package.json
└── .gitignore
```

## 环境要求

- WSL2 + Ubuntu 24.04（Windows 下开发）
- Python 3.12
- Node.js >= 22.12（Vite 8 要求）

## 启动方式

### 1. 后端（端口 8000）

```bash
cd ~/disaster-viz
source venv/bin/activate
uvicorn main:app --reload
```

验证：`http://localhost:8000/earthquakes?limit=3`

### 2. 前端（端口 5173）

新开一个终端：

```bash
cd ~/disaster-viz/frontend
npm run dev
```

浏览器打开 `http://localhost:5173`

> ⚠️ **两个服务都要开着**。前端从 `http://localhost:8000` 拉数据。

## API

### `GET /`

服务状态。

```json
{ "status": "ok", "project": "disaster-viz" }
```

### `GET /earthquakes`

查询参数：

| 参数 | 默认 | 说明 |
|------|------|------|
| `limit` | 100 | 返回条数 |
| `min_magnitude` | 2.5 | 最小震级 |

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

## 路线图

- [x] **W1** FastAPI 接入 USGS，浏览器可见 JSON
- [x] **W2** React + Leaflet 地图打点
- [ ] **W3** 交互完善（筛选 / 时间范围）+ Docker 化（`docker compose up` 一键起）
- [ ] **W4** PostgreSQL / PostGIS 落库 + 文档
- [ ] 第二版：接入 NASA FIRMS 野火数据
- [ ] 第三版：北欧 / 加拿大区域多灾种数据（雪崩 / 冻土）

## 开发备注

- GitHub 推送使用 Personal Access Token（不认密码）。
- 国内网络下 npm registry 建议指向镜像（本项目使用 `registry.npmmirror.com`）。
