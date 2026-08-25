import type { ElderTerminalApi } from './adapter';

/** 生产构建中的安全桩：任何 Mock 回落都会显式失败。 */
export class DemoAdapter implements ElderTerminalApi {
  constructor() {
    throw new Error('BFF_CONFIGURATION_REQUIRED');
  }

  private fail(): never { throw new Error('BFF_CONFIGURATION_REQUIRED'); }
  getDashboard(): never { return this.fail(); }
  getTasks(): never { return this.fail(); }
  getTimeline(): never { return this.fail(); }
  getAlerts(): never { return this.fail(); }
  submitRequest(): never { return this.fail(); }
  chat(): never { return this.fail(); }
  revokeConsent(): never { return this.fail(); }
  setFault(): void { this.fail(); }
  setAgentFault(): void { this.fail(); }
}
