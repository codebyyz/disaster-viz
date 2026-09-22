import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

// 后端地址（开发环境）
const API_URL = 'http://localhost:8000/earthquakes'
const DEFAULT_CENTER = [20, 0]
const DEFAULT_ZOOM = 2

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

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        const res = await fetch(API_URL)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setEarthquakes(data.earthquakes || [])
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Disaster Viz</h1>
        <p className="subtitle">全球地震实时可视化</p>
        <div className="status">
          {loading && <span className="badge loading">加载中…</span>}
          {error && <span className="badge error">错误：{error}</span>}
          {!loading && !error && (
            <span className="badge ok">共 {earthquakes.length} 条地震记录</span>
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
              fillOpacity: 0.6,
              weight: 1,
            }}
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
