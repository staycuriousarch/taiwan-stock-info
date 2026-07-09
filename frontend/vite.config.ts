import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 開發時把 /api 代理到 FastAPI 後端，前端就用相對路徑呼叫、免煩惱 CORS
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
