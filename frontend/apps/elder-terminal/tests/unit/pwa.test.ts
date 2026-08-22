import { describe, expect, it, vi } from 'vitest';
import { registerServiceWorker, type ServiceWorkerContainerLike } from '@/pwa/register';

function fakeContainer() {
  const listeners: Record<string, () => void> = {};
  const update = vi.fn().mockResolvedValue(undefined);
  const register = vi.fn().mockResolvedValue({ update });
  const addEventListener = vi.fn((type: string, fn: () => void) => {
    listeners[type] = fn;
  });
  const container: ServiceWorkerContainerLike = { register, addEventListener };
  return { listeners, update, register, container };
}

describe('service worker 注册与更新', () => {
  it('注册离线壳并检查更新', async () => {
    const { register, update, container } = fakeContainer();
    registerServiceWorker({ container });
    await Promise.resolve();

    expect(register).toHaveBeenCalledWith('/sw.js');
    expect(update).toHaveBeenCalled();
  });

  it('新版本接管页面时触发 onUpdateReady', async () => {
    const { listeners, container } = fakeContainer();
    const onUpdateReady = vi.fn();
    registerServiceWorker({ container, onUpdateReady });
    await Promise.resolve();

    expect(onUpdateReady).not.toHaveBeenCalled();
    listeners['controllerchange']();
    expect(onUpdateReady).toHaveBeenCalledTimes(1);
  });

  it('无 service worker 时静默降级', () => {
    const onUpdateReady = vi.fn();
    registerServiceWorker({ container: null, onUpdateReady });
    expect(onUpdateReady).not.toHaveBeenCalled();
  });
});
