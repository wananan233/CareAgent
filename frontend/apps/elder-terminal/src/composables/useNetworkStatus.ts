import { onMounted, onUnmounted } from 'vue';
import { useAppStore } from '@/stores/app';
import { useCareStore } from '@/stores/care';

/**
 * 跟踪浏览器在线/离线状态：首次挂载同步 navigator.onLine，
 * 之后监听 online/offline 事件；网络恢复时自动刷新数据。
 */
export function useNetworkStatus() {
  const app = useAppStore();
  const care = useCareStore();

  function handleOnline() {
    const wasOffline = app.offline;
    app.setOffline(false);
    if (wasOffline) {
      void care.recover();
    }
  }

  function handleOffline() {
    app.setOffline(true);
  }

  onMounted(() => {
    app.setOffline(typeof navigator !== 'undefined' && !navigator.onLine);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
  });

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  });
}
