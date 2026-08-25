import { describe, expect, it } from 'vitest';
import { makeCareRequest } from '@carehub/shared-contracts/elder';
import { CoreApiAdapter } from '@/services/CoreApiAdapter';
import type { ElderTerminalApi } from '@/services/adapter';

const now = '2026-08-25T08:00:00.000Z';
function api() {
  const fetcher: typeof fetch = async (input) => {
    const path = String(input);
    const body = path.endsWith('/tasks') ? { items: [{ task_ref: 'task:one', status: 'DUE', evidence_state: 'UNKNOWN', scheduled_at: now, version: 1, source_refs: ['evt-1'] }] }
      : path.endsWith('/alerts') ? { items: [{ alert_id: 'alert:one', kind: 'SMOKE_GAS', safety_level: 'S0', status: 'OPEN', occurred_at: now, version: 1, quality: 'HIGH', source_refs: ['evt-2'] }] }
      : path.endsWith('/timeline') ? { items: [{ event_id: 'evt-1', event_type: 'MEDICATION_DUE', occurred_at: now }] }
      : path.endsWith('/dashboard') ? { snapshot_id: 'snapshot-1', server_time: now, last_updated_at: now, quality: 'HIGH' }
      : path.endsWith('/report') ? { schema_version: 'AgentResponseV1', response_id: 'response-1', agent_run_id: 'run-1', channel: 'TERMINAL', message: '仅基于授权记录。', facts: [{ text: '任务待确认。', source_refs: ['evt-1'] }], fallback: 'NONE', generator_version: 'fake-llm.g4.v1' }
      : { request_id: 'request-1', audit_time: now, alert_id: 'task:one', status: 'RECORDED' };
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  return new CoreApiAdapter({ baseUrl: 'https://bff.example', token: 'test-token', householdId: 'home:a', fetcher });
}

describe('CoreApiAdapter', () => {
  it('与 ElderTerminalApi 契约一致（真实 BFF 配置必填）', () => {
    const core: ElderTerminalApi = api();
    expect(core).toBeDefined();
  });

  it('将受保护 BFF 视图映射为老人端 DTO', async () => {
    const core = api();
    const [dashboard, tasks, alerts, timeline, chat, receipt] = await Promise.all([
      core.getDashboard('user:alice'), core.getTasks('user:alice'), core.getAlerts('user:alice'), core.getTimeline('user:alice'), core.chat('user:alice', '今天怎么样？'), core.submitRequest('user:alice', makeCareRequest({ target_id: 'task:one' })),
    ]);
    expect(dashboard.ok && dashboard.data.primaryTask?.task_id).toBe('task:one');
    expect(tasks.ok && tasks.data[0].source_refs[0].type).toBe('SIMULATOR');
    expect(alerts.ok && alerts.data[0].quality).toBe('VALID');
    expect(timeline.ok && timeline.data[0].event_type).toBe('MEDICATION_DUE');
    expect(chat.ok && chat.data.facts[0].source_refs).toEqual(['evt-1']);
    expect(receipt.ok && receipt.data.status).toBe('RECORDED');
  });

  it('网络失败显式降级为 NETWORK_OFFLINE', async () => {
    const core = new CoreApiAdapter({ baseUrl: 'https://bff.example', token: 'test-token', householdId: 'home:a', fetcher: async () => { throw new TypeError('network'); } });
    const result = await core.getTasks('user:alice');
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.reason_code).toBe('NETWORK_OFFLINE');
  });
});
