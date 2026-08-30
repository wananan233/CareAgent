import type { CoreAdapter } from './CoreApiAdapter'

/** 生产构建中的安全桩：任何 Mock 回落都会显式失败。 */
export class DemoAdapter implements CoreAdapter {
  constructor() {
    throw new Error('BFF_CONFIGURATION_REQUIRED')
  }

  private fail(): never { throw new Error('BFF_CONFIGURATION_REQUIRED') }
  getDashboard(): never { return this.fail() }
  getAlerts(): never { return this.fail() }
  acknowledgeAlert(): never { return this.fail() }
  getTasks(): never { return this.fail() }
  getTimeline(): never { return this.fail() }
  createCareRequest(): never { return this.fail() }
  getAgent(): never { return this.fail() }
  askReadOnly(): never { return this.fail() }
  revokeConsent(): never { return this.fail() }
  relinquishConsent(): never { return this.fail() }
}
