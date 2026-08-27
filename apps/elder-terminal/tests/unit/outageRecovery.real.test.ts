import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { CoreApiAdapter } from '@/services/CoreApiAdapter';
import { useCareStore } from '@/stores/care';
import { i0Tokens, startI0Bff } from '../../../test-support/i0Bff';

const waitFor = async (check: () => boolean, timeout = 5_000) => {
  const end = Date.now() + timeout;
  while (Date.now() < end) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 25)); }
  throw new Error('恢复超时');
};
let bff: Awaited<ReturnType<typeof startI0Bff>>;
let restarted: Awaited<ReturnType<typeof startI0Bff>> | undefined;
beforeAll(async () => { bff = await startI0Bff(); }, 15_000);
afterAll(async () => { await restarted?.stop(); await bff?.stop(); });

describe.sequential('Elder 真实 BFF outage 自动恢复', () => {
  it('保留可信快照，same-port restart 后仅靠 GET 自动恢复且不重放 command', async () => {
    setActivePinia(createPinia());
    const care = useCareStore();
    care.subjectId = 'user:elder-a' as typeof care.subjectId;
    care.api = new CoreApiAdapter({ baseUrl: bff.baseUrl, token: i0Tokens.elderA, householdId: 'household:i0-a' }) as unknown as typeof care.api;
    await care.refresh();
    expect(care.lastTrustedAt).not.toBeNull();
    const taskCount = care.tasks.length;
    const receipt = care.receipt;
    await bff.stop();
    await care.refresh();
    expect(care.loadError).toBe('NETWORK_OFFLINE');
    expect(care.stale).toBe(true);
    expect(care.tasks).toHaveLength(taskCount);
    const port = Number(new URL(bff.baseUrl).port);
    restarted = await startI0Bff({ port });
    await waitFor(() => care.loadError === null && !care.stale && care.tasks.length === taskCount);
    expect(care.receipt).toBe(receipt);
    expect(care.pendingResubmit).toBeNull();
  }, 15_000);
});
