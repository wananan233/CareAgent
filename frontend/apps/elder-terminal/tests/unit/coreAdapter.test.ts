import { describe, expect, it } from 'vitest';
import { makeCareRequest } from '@carehub/shared-contracts';
import { CoreApiAdapter } from '@/services/CoreApiAdapter';
import type { ElderTerminalApi } from '@/services/adapter';

describe('CoreApiAdapter', () => {
  it('与 ElderTerminalApi 契约一致（可赋值，接口冻结）', () => {
    const api: ElderTerminalApi = new CoreApiAdapter();
    expect(api).toBeDefined();
  });

  it('C0-C4 就绪前，所有端点返回 NOT_IMPLEMENTED', async () => {
    const api = new CoreApiAdapter();
    const results = await Promise.all([
      api.getDashboard('subject-sim-001'),
      api.getTasks('subject-sim-001'),
      api.getTimeline('subject-sim-001'),
      api.getAlerts('subject-sim-001'),
      api.submitRequest('subject-sim-001', makeCareRequest()),
      api.chat('subject-sim-001', '你好'),
      api.revokeConsent('subject-sim-001', 'timeline'),
    ]);
    for (const r of results) {
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.error.error.code).toBe('NOT_IMPLEMENTED');
    }
  });
});
