import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE streams need this disabled
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Keep SSE connections alive
            proxyRes.headers['cache-control'] = 'no-cache';
          });
        },
      },
    },
  },
})
