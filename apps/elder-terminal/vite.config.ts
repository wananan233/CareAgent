import { fileURLToPath, URL } from 'node:url';
import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vitest/config';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'CareHub 老人端（模拟演示）',
        short_name: 'CareHub 老人端',
        display: 'standalone',
        theme_color: '#10213b',
        background_color: '#f4f7fb',
        icons: [],
      },
    }),
  ],
  resolve: {
    alias: [
      {
        find: '@carehub/mock-runtime',
        replacement: fileURLToPath(new URL(
          mode === 'production' ? './src/services/mock-runtime.production.ts' : './src/services/mock-runtime.ts',
          import.meta.url,
        )),
      },
      { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
    ],
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
  },
}));
