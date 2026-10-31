import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 开发时把 /earthquakes 代理到本地后端，
    // 这样前端代码里可以直接用相对路径，开发和生产行为一致。
    proxy: {
      '/earthquakes': 'http://127.0.0.1:8000',
      '/fires': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
