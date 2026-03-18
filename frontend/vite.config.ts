import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: {
    outDir: '../engine/gui/static',
    emptyOutDir: true,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/notes': 'http://127.0.0.1:37491',
      '/search': 'http://127.0.0.1:37491',
      '/events': 'http://127.0.0.1:37491',
      '/actions': 'http://127.0.0.1:37491',
      '/files': 'http://127.0.0.1:37491',
      '/capture': 'http://127.0.0.1:37491',
      '/intelligence': 'http://127.0.0.1:37491',
      '/brain-health': 'http://127.0.0.1:37491',
      '/ui': 'http://127.0.0.1:37491',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
