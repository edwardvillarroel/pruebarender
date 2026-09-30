import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/ApoloVibes3D-Frontend/',
  server: {
    port: 5173,
    proxy: {
      // 127.0.0.1 y no "localhost": en Windows "localhost" resuelve a ::1, el
      // gateway escucha solo en IPv4 y cada /api tardaba ~2s en el proxy.
      '/api': 'http://127.0.0.1:3000'
    }
  }
})
