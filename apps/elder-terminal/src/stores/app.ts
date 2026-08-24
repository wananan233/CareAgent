import { defineStore } from 'pinia';

/** 可选字号档位（正文按 --font-scale 缩放，最低档仍满足 20px 底线）。 */
export type FontScale = 1 | 1.25 | 1.5;
export const FONT_SCALE_OPTIONS: FontScale[] = [1, 1.25, 1.5];

/** 仅保存 UI 与短期状态；业务事实源只能是服务端（snapshot/version/source/quality）。 */
export const useAppStore = defineStore('app', {
  state: () => ({
    fontScale: 1 as FontScale,
    soundEnabled: false,
    nonCriticalReminders: true,
    offline: false,
    lastSyncAt: null as string | null,
    errorCode: null as string | null,
    updateReady: false,
  }),
  actions: {
    setFontScale(scale: FontScale) {
      this.fontScale = scale;
    },
    setSoundEnabled(enabled: boolean) {
      this.soundEnabled = enabled;
    },
    setNonCriticalReminders(enabled: boolean) {
      this.nonCriticalReminders = enabled;
    },
    setOffline(offline: boolean) {
      this.offline = offline;
    },
    setLastSyncAt(at: string | null) {
      this.lastSyncAt = at;
    },
    setErrorCode(code: string | null) {
      this.errorCode = code;
    },
    /** service worker 新版本已就绪（刷新后生效）。 */
    setUpdateReady(ready: boolean) {
      this.updateReady = ready;
    },
    /** 模拟重新联网：清除离线与错误标记。真实重试由 CoreApiAdapter 在后续阶段接管。 */
    retry() {
      this.offline = false;
      this.errorCode = null;
    },
  },
});
