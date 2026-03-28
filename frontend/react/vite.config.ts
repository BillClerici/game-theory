import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://web:8000', changeOrigin: false },
      '/auth': { target: 'http://web:8000', changeOrigin: false },
      '/health': { target: 'http://web:8000', changeOrigin: false },
      '/graphql': { target: 'http://web:8000', changeOrigin: false },
    },
  },
})
