import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',  // Force IPv4
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',  // Use explicit IPv4
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8001',  // Use explicit IPv4
        ws: true,
        timeout: 0,  // Disable timeout for WebSocket
      },
    },
  },
})
