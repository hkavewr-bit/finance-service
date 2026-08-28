import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    proxy: {
      // 客服后端
      '/api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
      // 数据中台（业务对象侧栏数据源）
      '/finance': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/finance/, '/api/v1'),
      },
    },
  },
})
