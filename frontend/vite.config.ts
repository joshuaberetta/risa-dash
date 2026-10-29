import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the Django API runs in docker compose on :8070.
const api = process.env.API_URL || 'http://localhost:8070'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // The print worker's Chromium (in docker) reaches the dev server as host.docker.internal
    allowedHosts: ['localhost', 'host.docker.internal'],
    proxy: {
      '/api': api,
      '/media': api,
      '/admin': api,
      '/static': api,
    },
    fs: { allow: ['..'] },
  },
  build: { chunkSizeWarningLimit: 2500 },
})
