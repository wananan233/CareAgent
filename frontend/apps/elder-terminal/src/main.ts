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

registerServiceWorker({
  onUpdateReady: () => useAppStore(pinia).setUpdateReady(true),
});
