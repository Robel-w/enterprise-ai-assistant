import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE streams need this disabled
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Keep SSE connections alive
            proxyRes.headers['cache-control'] = 'no-cache';
          });
        },
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
