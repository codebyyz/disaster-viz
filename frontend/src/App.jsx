import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

// 后端地址。默认空字符串 = 同源相对路径：
//   - Vite dev server 下由 vite.config.js 的 proxy 转发到 :8000
//   - Docker 下前后端同一个端口，直接就是同源
// 只有前后端跨域部署时才需要设 VITE_API_BASE=http://host:port
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEFAULT_CENTER = [20, 0]
const DEFAULT_ZOOM = 2

// 时间窗口选项（天）。50 年 + 极低震级会让 USGS 返回上万条，故意不给。
const DAY_OPTIONS = [
  { label: '24 小时', value: 1 },
  { label: '7 天', value: 7 },
  { label: '30 天', value: 30 },
  { label: '90 天', value: 90 },
]

const MAG_OPTIONS = [
  { label: '全部', value: 0 },
  { label: 'M2.5+', value: 2.5 },
  { label: 'M4.5+', value: 4.5 },
  { label: 'M6+', value: 6 },
]

/**
 * 按震级决定圆圈半径（震级越大，圈越大）
 */
function radiusForMagnitude(mag) {
  if (mag == null) return 3
  return Math.max(3, mag * 3)
}

/**
 * 按震级决定颜色（浅黄 → 橙 → 红）
 */
function colorForMagnitude(mag) {
  if (mag == null) return '#888'
  if (mag >= 6) return '#dc2626'
  if (mag >= 5) return '#ea580c'
  if (mag >= 3) return '#f59e0b'
  return '#fbbf24'
}

function App() {
  const [earthquakes, setEarthquakes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 筛选状态 = 请求参数。改筛选 -> 重新请求 -> 后端让 USGS 过滤。
  const [days, setDays] = useState(7)
  const [minMag, setMinMag] = useState(2.5)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchData() {
      try {
        setLoading(true)
        const params = new URLSearchParams({
          days: String(days),
          min_magnitude: String(minMag),
          limit: '2000',
        })
        const res = await fetch(`${API_BASE}/earthquakes?${params}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setEarthquakes(data.earthquakes || [])
        setError(null)
      } catch (err) {
        // 切换筛选时上一次请求会被 abort，这不是错误，忽略。
        if (err.name === 'AbortError') return
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    return () => controller.abort()
  }, [days, minMag])

  // 统计信息由前端算：当前渲染的数据集里最强的一次、平均深度等。
  const stats = useMemo(() => {
    if (earthquakes.length === 0) return null
    let strongest = earthquakes[0]
    let depthSum = 0
    let depthCount = 0
    for (const eq of earthquakes) {
      if (eq.magnitude != null && eq.magnitude > (strongest.magnitude ?? -Infinity)) {
        strongest = eq
      }
      if (eq.depth != null) {
        depthSum += eq.depth
        depthCount += 1
      }
    }
    return {
      strongest,
      avgDepth: depthCount ? (depthSum / depthCount).toFixed(1) : '—',
    }
  }, [earthquakes])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-top">
          <div>
            <h1>Disaster Viz</h1>
            <p className="subtitle">全球地震实时可视化</p>
          </div>
          <div className="status">
            {loading && <span className="badge loading">加载中…</span>}
            {error && <span className="badge error">错误：{error}</span>}
            {!loading && !error && (
              <span className="badge ok">共 {earthquakes.length} 条</span>
            )}
          </div>
        </div>

        <div className="filters">
          <label className="filter">
            时间窗口
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              {DAY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <label className="filter">
            最小震级
            <select
              value={minMag}
              onChange={(e) => setMinMag(Number(e.target.value))}
            >
              {MAG_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          {stats && (
            <div className="stats">
              <span>
                最强 <b>M {stats.strongest.magnitude}</b>
                {' · '}
                {stats.strongest.place}
              </span>
              <span>平均深度 {stats.avgDepth} km</span>
            </div>
          )}
        </div>
      </header>

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        className="map"
        worldCopyJump={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {earthquakes.map((eq) => (
          <CircleMarker
            key={eq.id}
            center={[eq.lat, eq.lon]}
            radius={radiusForMagnitude(eq.magnitude)}
            pathOptions={{
              color: colorForMagnitude(eq.magnitude),
              fillColor: colorForMagnitude(eq.magnitude),
              fillOpacity: selected === eq.id ? 0.9 : 0.6,
              weight: selected === eq.id ? 3 : 1,
            }}
            eventHandlers={{ click: () => setSelected(eq.id) }}
          >
            <Popup>
              <div className="popup">
                <strong>M {eq.magnitude}</strong>
                <br />
                {eq.place}
                <br />
                <span className="muted">
                  深度 {eq.depth} km · {new Date(eq.time).toLocaleString()}
                </span>
                <br />
                <a
                  className="usgs-link"
                  href={`https://earthquake.usgs.gov/earthquakes/eventpage/${eq.id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  查看 USGS 详情 →
                </a>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      <footer className="app-footer">
        <span>数据来源：USGS Earthquake API</span>
        <span className="legend">
          <i style={{ background: '#fbbf24' }} /> M&lt;3
          <i style={{ background: '#f59e0b' }} /> M3-5
          <i style={{ background: '#ea580c' }} /> M5-6
          <i style={{ background: '#dc2626' }} /> M6+
        </span>
      </footer>
    </div>
  )
}

export default App
