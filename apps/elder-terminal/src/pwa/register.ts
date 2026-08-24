/** 可注入的 service worker 注册接口（便于单测 mock）。 */
export interface ServiceWorkerRegistrationLike {
  update?: () => Promise<unknown>;
}

export interface ServiceWorkerContainerLike {
  register: (path: string) => Promise<ServiceWorkerRegistrationLike>;
  addEventListener: (type: string, listener: () => void) => void;
}

export interface RegisterServiceWorkerOptions {
  onUpdateReady?: () => void;
  swPath?: string;
  container?: ServiceWorkerContainerLike | null;
}

/**
 * 注册离线壳 service worker，并检测“新版本已就绪”。
 * 新 worker 激活并接管页面（controllerchange）后触发 onUpdateReady。
 * 浏览器不支持 SW（或测试环境未注入）时静默降级。
 */
export function registerServiceWorker(options: RegisterServiceWorkerOptions = {}): void {
  const { onUpdateReady, swPath = '/sw.js', container } = options;
  const sw: ServiceWorkerContainerLike | null =
    container ??
    (typeof navigator !== 'undefined' && 'serviceWorker' in navigator
      ? (navigator.serviceWorker as unknown as ServiceWorkerContainerLike)
      : null);
  if (!sw) return;

  sw.register(swPath)
    .then((registration) => {
      if (onUpdateReady) {
        sw.addEventListener('controllerchange', onUpdateReady);
      }
      registration.update?.().catch(() => {
        /* 更新检查失败可忽略，不阻断应用 */
      });
    })
    .catch(() => {
      /* 非 https 或 dev 下注册失败，静默降级 */
    });
}
