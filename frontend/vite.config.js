import { defineConfig } from 'vite'

export default defineConfig({
  server: { proxy: Object.fromEntries(
    ['/login', '/me', '/chat', '/ingest', '/admin'].map(path => [path, 'http://localhost:8000'])
  ) }
})
