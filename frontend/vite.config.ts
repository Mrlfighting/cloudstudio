import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      // 开发代理：浏览器视角同源（localhost:5173），会话/CSRF cookie 自动携带，无需 CORS
      // 不 rewrite：后端路由本身是 /api/v1/...
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true, // 代理 WebSocket 升级（图片协同编辑）
      },
    },
  },
})
