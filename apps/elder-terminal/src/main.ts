import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import { useAppStore } from './stores/app';
import { registerServiceWorker } from './pwa/register';
import './styles/tokens.css';

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);
app.mount('#app');

// Vite 开发服务器不会提供生产 SW 文件；仅生产构建注册，避免 /sw.js 回退 HTML 的 MIME 警告。
if (import.meta.env.PROD) {
  registerServiceWorker({
    onUpdateReady: () => useAppStore(pinia).setUpdateReady(true),
  });
}
