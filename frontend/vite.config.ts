import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  // `python backend/server.py` serves the API (and the built app) on :8000.
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
