import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'CareHub 家属端（模拟演示）',
        short_name: 'CareHub 家属端',
        display: 'standalone',
        theme_color: '#f2f2f7',
        background_color: '#f2f2f7',
        icons: []
      }
    })
  ],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: { environment: 'jsdom', globals: true, exclude: ['tests/e2e/**'] }
})
