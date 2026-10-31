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

// 数据源类型。第二版起，页面顶部用 tab 切换「地震 / 野火」。
// 每个源有自己的一套筛选选项、颜色规则、图例说明。
const SOURCES = {
  earthquakes: {
    label: '地震',
    subtitle: '全球地震实时可视化',
    endpoint: '/earthquakes',
    dataKey: 'earthquakes',
  },
  fires: {
    label: '野火',
    subtitle: '全球野火热点（NASA FIRMS）',
    endpoint: '/fires',
    dataKey: 'fires',
  },
}

// 地震：时间窗口（天）
const EQ_DAY_OPTIONS = [
  { label: '24 小时', value: 1 },
  { label: '7 天', value: 7 },
  { label: '30 天', value: 30 },
  { label: '90 天', value: 90 },
]

const EQ_MAG_OPTIONS = [
  { label: '全部', value: 0 },
  { label: 'M2.5+', value: 2.5 },
  { label: 'M4.5+', value: 4.5 },
  { label: 'M6+', value: 6 },
]

// 野火：时间窗口（FIRMS 上限 5 天）
const FIRE_DAY_OPTIONS = [
  { label: '24 小时', value: 1 },
  { label: '2 天', value: 2 },
  { label: '3 天', value: 3 },
  { label: '5 天', value: 5 },
]

/**
 * 地震：按震级决定圆圈半径（震级越大，圈越大）
 */
function radiusForMagnitude(mag) {
  if (mag == null) return 3
  return Math.max(3, mag * 3)
}

/**
 * 地震：按震级决定颜色（浅黄 → 橙 → 红）
 */
function colorForMagnitude(mag) {
  if (mag == null) return '#888'
  if (mag >= 6) return '#dc2626'
  if (mag >= 5) return '#ea580c'
  if (mag >= 3) return '#f59e0b'
  return '#fbbf24'
}

/**
 * 野火：按亮温 bright_ti4（开尔文）决定颜色。
 * 亮温越高火越强：低温橙 → 高温亮红。
 * 阈值是经验值：~300K 是常温背景，300-340K 低温火，340K+ 高温火。
 */
function colorForFire(bright) {
  if (bright == null) return '#f59e0b'
  if (bright >= 350) return '#dc2626'
  if (bright >= 330) return '#ea580c'
  if (bright >= 310) return '#f59e0b'
  return '#fb923c'
}

/**
 * 野火：亮温也能反映点的大小（轻微），但别做太夸张。
 */
function radiusForFire(bright) {
  if (bright == null) return 4
  return Math.max(4, Math.min(10, (bright - 300) * 0.5))
}

function App() {
  const [source, setSource] = useState('earthquakes')
  const [data, setData] = useState([])
  const [meta, setMeta] = useState({ total: null, sampled: false, demo: false })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  // 地震筛选状态
  const [days, setDays] = useState(7)
  const [minMag, setMinMag] = useState(2.5)
  // 野火筛选状态单独存 —— 两个源的可选范围不同（地震到 90 天，
  // 野火最多 5 天）。共用一个 days 会导致切 tab 时 select 显示空值、
  // 并发出超范围的请求。分开存是最省心且行为正确的做法。
  const [fireDays, setFireDays] = useState(1)

  const cfg = SOURCES[source]
  // 当前源实际生效的时间窗口，统一取一个变量供请求与 select 使用。
  const activeDays = source === 'earthquakes' ? days : fireDays
  const setActiveDays = source === 'earthquakes' ? setDays : setFireDays

  // 切换数据源时清空选中的点，避免残留高亮。
  useEffect(() => {
    setSelected(null)
  }, [source])

  useEffect(() => {
    const controller = new AbortController()

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        let res
        if (source === 'earthquakes') {
          const params = new URLSearchParams({
            days: String(days),
            min_magnitude: String(minMag),
            limit: '2000',
          })
          res = await fetch(`${API_BASE}${cfg.endpoint}?${params}`, {
            signal: controller.signal,
          })
        } else {
          // 野火：只透传 days；sensor 交给后端默认值。
          // limit 让后端做降采样保护 —— FIRMS 全球单日热点可达数万条，
          // 全量传给 Leaflet 会把浏览器卡死。
          const params = new URLSearchParams({
            days: String(fireDays),
            limit: '3000',
          })
          res = await fetch(`${API_BASE}${cfg.endpoint}?${params}`, {
            signal: controller.signal,
          })
        }
        if (!res.ok) {
          // 400 通常是没配 MAP_KEY，把后端 detail 透出来提示用户。
          let detail = `HTTP ${res.status}`
          try {
            const body = await res.json()
            if (body.detail) detail = body.detail
          } catch {
            /* ignore */
          }
          throw new Error(detail)
        }
        const json = await res.json()
        setData(json[cfg.dataKey] || [])
        // FIRMS 数据量大时后端会降采样，把总量与采样标记交给 UI 提示。
        setMeta({
          total: json.total ?? null,
          sampled: Boolean(json.sampled),
          demo: json.source === 'firms-demo',
        })
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
  }, [source, days, fireDays, minMag, cfg.endpoint, cfg.dataKey])

  // 统计信息：地震看最强震/平均深度；野火看最高亮温/平均 FRP。
  const stats = useMemo(() => {
    if (data.length === 0) return null
    if (source === 'earthquakes') {
      let strongest = data[0]
      let depthSum = 0
      let depthCount = 0
      for (const eq of data) {
        if (eq.magnitude != null && eq.magnitude > (strongest.magnitude ?? -Infinity)) {
          strongest = eq
        }
        if (eq.depth != null) {
          depthSum += eq.depth
          depthCount += 1
        }
      }
      return {
        primary: `最强 M ${strongest.magnitude ?? '—'} · ${strongest.place ?? ''}`,
        secondary: `平均深度 ${depthCount ? (depthSum / depthCount).toFixed(1) : '—'} km`,
      }
    }
    // 野火统计
    let hottest = data[0]
    let frpSum = 0
    let frpCount = 0
    for (const f of data) {
      if (f.bright_ti4 != null && f.bright_ti4 > (hottest.bright_ti4 ?? -Infinity)) {
        hottest = f
      }
      if (f.frp != null) {
        frpSum += f.frp
        frpCount += 1
      }
    }
    return {
      primary: `最高亮温 ${hottest.bright_ti4 != null ? `${Math.round(hottest.bright_ti4)}K` : '—'}`,
      secondary: `平均 FRP ${frpCount ? (frpSum / frpCount).toFixed(1) : '—'} MW`,
    }
  }, [data, source])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-top">
          <div>
            <h1>Disaster Viz</h1>
            <p className="subtitle">{cfg.subtitle}</p>
          </div>
          <div className="status">
            {meta.demo && <span className="badge demo">演示数据</span>}
            {loading && <span className="badge loading">加载中…</span>}
            {error && <span className="badge error">错误：{error}</span>}
            {!loading && !error && (
              <span className="badge ok">
                共 {data.length} 条
                {meta.sampled && meta.total ? ` / ${meta.total}（已按强度取前 ${data.length}）` : ''}
              </span>
            )}
          </div>
        </div>

        {/* 数据源切换 tab */}
        <div className="tabs">
          {Object.entries(SOURCES).map(([key, s]) => (
            <button
              key={key}
              className={`tab ${source === key ? 'active' : ''}`}
              onClick={() => setSource(key)}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="filters">
          <label className="filter">
            时间窗口
            <select value={activeDays} onChange={(e) => setActiveDays(Number(e.target.value))}>
              {(source === 'earthquakes' ? EQ_DAY_OPTIONS : FIRE_DAY_OPTIONS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          {source === 'earthquakes' && (
            <label className="filter">
              最小震级
              <select value={minMag} onChange={(e) => setMinMag(Number(e.target.value))}>
                {EQ_MAG_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          {stats && (
            <div className="stats">
              <span>{stats.primary}</span>
              <span>{stats.secondary}</span>
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

        {data.map((d) => {
          const isFire = source === 'fires'
          const val = isFire ? d.bright_ti4 : d.magnitude
          const color = isFire ? colorForFire(val) : colorForMagnitude(val)
          const radius = isFire ? radiusForFire(val) : radiusForMagnitude(val)
          return (
            <CircleMarker
              key={d.id}
              center={[d.lat, d.lon]}
              radius={radius}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: selected === d.id ? 0.9 : 0.6,
                weight: selected === d.id ? 3 : 1,
              }}
              eventHandlers={{ click: () => setSelected(d.id) }}
            >
              <Popup>
                <div className="popup">
                  {isFire ? (
                    <>
                      <strong>{d.bright_ti4 != null ? `${Math.round(d.bright_ti4)}K` : '—'}</strong>
                      <br />
                      传感器 {d.satellite} · {d.instrument}
                      <br />
                      <span className="muted">
                        置信度 {d.confidence ?? '—'} ·{' '}
                        {d.daynight === 'D' ? '昼' : '夜'} ·{' '}
                        {d.time ? new Date(d.time).toLocaleString() : '—'}
                      </span>
                      {d.frp != null && (
                        <>
                          <br />
                          FRP {d.frp.toFixed(1)} MW
                        </>
                      )}
                    </>
                  ) : (
                    <>
                      <strong>M {d.magnitude}</strong>
                      <br />
                      {d.place}
                      <br />
                      <span className="muted">
                        深度 {d.depth} km · {new Date(d.time).toLocaleString()}
                      </span>
                      <br />
                      <a
                        className="usgs-link"
                        href={`https://earthquake.usgs.gov/earthquakes/eventpage/${d.id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        查看 USGS 详情 →
                      </a>
                    </>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>

      <footer className="app-footer">
        <span>
          {source === 'earthquakes'
            ? '数据来源：USGS Earthquake API'
            : meta.demo
              ? '数据来源：NASA FIRMS（演示数据，未接入真实 key）'
              : '数据来源：NASA FIRMS'}
        </span>
        {source === 'earthquakes' ? (
          <span className="legend">
            <i style={{ background: '#fbbf24' }} /> M&lt;3
            <i style={{ background: '#f59e0b' }} /> M3-5
            <i style={{ background: '#ea580c' }} /> M5-6
            <i style={{ background: '#dc2626' }} /> M6+
          </span>
        ) : (
          <span className="legend">
            <i style={{ background: '#fb923c' }} /> &lt;310K
            <i style={{ background: '#f59e0b' }} /> 310-330K
            <i style={{ background: '#ea580c' }} /> 330-350K
            <i style={{ background: '#dc2626' }} /> 350K+
          </span>
        )}
      </footer>
    </div>
  )
}

export default App
