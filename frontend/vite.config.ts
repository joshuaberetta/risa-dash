import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// In development the Django API runs in docker compose on :8070.
const api = process.env.API_URL || 'http://localhost:8070'

// The user guide is a static page (public/guide/index.html), outside the React app. In
// production Django serves it at /guide/ (risa/views.py guide); here the same.
const guide: Plugin = {
  name: 'risa-guide',
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const path = req.url?.split('?')[0]
      if (path === '/guide') { res.statusCode = 301; res.setHeader('Location', '/guide/'); res.end(); return }
      if (path === '/guide/') req.url = '/guide/index.html'
      next()
    })
  },
}

export default defineConfig({
  plugins: [react(), guide],
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
