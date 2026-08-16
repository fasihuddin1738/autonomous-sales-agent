import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/outreach': 'http://127.0.0.1:8000',
      '/discovery': 'http://127.0.0.1:8000',
      '/research': 'http://127.0.0.1:8000',
    },
  },
})
