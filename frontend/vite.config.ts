import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Echo · Vite 配置
// 通过 server.proxy 让前端 dev 直接调 /api/* 反代到后端 8000
// 生产环境前端打包后由腾讯云 CDN 托管，/api 由网关转发到后端
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
