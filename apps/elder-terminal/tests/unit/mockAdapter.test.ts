import { describe, expect, it } from 'vitest';
import {
  isAgentResponseV1,
  isAlertViewV1,
  isCareEventV1,
  isCareTaskV1,
  isConsentViewV1,
  isDashboardViewV1,
  isErrorEnvelope,
  isRequestReceiptV1,
  makeCareRequest,
} from '@carehub/shared-contracts/elder';
import { MockCoreAdapter } from '@/services/MockCoreAdapter';
import { DEMO_SUBJECT_ID } from '@/scenarios/fixtures';

describe('MockCoreAdapter 各结果状态', () => {
  it('默认（happy）返回通过 guard 的合法数据', async () => {
    const api = new MockCoreAdapter();

    const dash = await api.getDashboard(DEMO_SUBJECT_ID);
    expect(dash.ok).toBe(true);
    if (dash.ok) expect(isDashboardViewV1(dash.data)).toBe(true);

    const tasks = await api.getTasks(DEMO_SUBJECT_ID);
    expect(tasks.ok).toBe(true);
    if (tasks.ok) {
      expect(tasks.data.length).toBeGreaterThan(0);
      expect(tasks.data.every(isCareTaskV1)).toBe(true);
    }

    const timeline = await api.getTimeline(DEMO_SUBJECT_ID);
    expect(timeline.ok).toBe(true);
    if (timeline.ok) expect(timeline.data.every(isCareEventV1)).toBe(true);

    const alerts = await api.getAlerts(DEMO_SUBJECT_ID);
    expect(alerts.ok).toBe(true);
    if (alerts.ok) expect(alerts.data.every(isAlertViewV1)).toBe(true);

    const chat = await api.chat(DEMO_SUBJECT_ID, '你好');
    expect(chat.ok).toBe(true);
    if (chat.ok) expect(isAgentResponseV1(chat.data)).toBe(true);

    const firstTask = tasks.ok ? tasks.data[0] : null;
    expect(firstTask).toBeTruthy();
    const receipt = await api.submitRequest(
      DEMO_SUBJECT_ID,
      makeCareRequest({
        kind: 'ACKNOWLEDGE_TASK',
        target_id: firstTask!.task_id,
        expected_version: firstTask!.version,
      }),
    );
    expect(receipt.ok).toBe(true);
    if (receipt.ok) expect(isRequestReceiptV1(receipt.data)).toBe(true);

    const consent = await api.revokeConsent(DEMO_SUBJECT_ID, 'timeline');
    expect(consent.ok).toBe(true);
    if (consent.ok) {
      expect(isConsentViewV1(consent.data)).toBe(true);
      expect(consent.data.status).toBe('REVOKED');
    }
  });

  it('空输入对话返回家庭端契约的模板 fallback', async () => {
    const api = new MockCoreAdapter();
    const r = await api.chat(DEMO_SUBJECT_ID, '   ');
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.data.fallback).toBe('TEMPLATE_FALLBACK');
    }
  });

  it('offline 故障返回 OFFLINE/NETWORK_OFFLINE 信封', async () => {
    const api = new MockCoreAdapter({ fault: 'offline' });
    const r = await api.getDashboard(DEMO_SUBJECT_ID);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(isErrorEnvelope(r.error)).toBe(true);
      expect(r.error.code).toBe('OFFLINE');
      expect(r.error.reason_code).toBe('NETWORK_OFFLINE');
    }
  });

  it('denied 故障返回 FORBIDDEN/SUBJECT_MISMATCH', async () => {
    const api = new MockCoreAdapter({ fault: 'denied' });
    const r = await api.getTasks(DEMO_SUBJECT_ID);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.code).toBe('FORBIDDEN');
  });

  it('failed 故障返回 UNAVAILABLE/UPSTREAM_FAILED 且可重试', async () => {
    const api = new MockCoreAdapter({ fault: 'failed' });
    const r = await api.getAlerts(DEMO_SUBJECT_ID);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.error.code).toBe('UNAVAILABLE');
      expect(r.error.retryable).toBe(true);
    }
  });
});

describe('getTimeline 时间线', () => {
  it('返回合法事件，且含 MEDICATION_DUE 与 LOW/CONFLICT 质量', async () => {
    const api = new MockCoreAdapter();
    const r = await api.getTimeline(DEMO_SUBJECT_ID);
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.data.every(isCareEventV1)).toBe(true);
      expect(r.data.some((e) => e.event_type === 'MEDICATION_DUE')).toBe(true);
      expect(r.data.some((e) => e.quality.status === 'LOW')).toBe(true);
      expect(r.data.some((e) => e.quality.status === 'CONFLICT')).toBe(true);
    }
  });
});

describe('幂等请求与版本控制', () => {
  it('同一 idempotency_key 重复提交只生效一次（版本仅 +1）', async () => {
    const api = new MockCoreAdapter();
    const tasks = await api.getTasks(DEMO_SUBJECT_ID);
    expect(tasks.ok).toBe(true);
    const task = tasks.ok ? tasks.data[0] : null;
    expect(task).toBeTruthy();

    const req = makeCareRequest({
      kind: 'ACKNOWLEDGE_TASK',
      target_id: task!.task_id,
      expected_version: task!.version,
    });

    const r1 = await api.submitRequest(DEMO_SUBJECT_ID, req);
    const r2 = await api.submitRequest(DEMO_SUBJECT_ID, req);
    expect(r1.ok).toBe(true);
    expect(r2.ok).toBe(true);
    if (r1.ok && r2.ok) {
      expect(r1.data.status).toBe('RECORDED');
      expect(r2.data.status).toBe('RECORDED');
      expect(r2.data.request_id).toBe(req.command_id);
    }

    const after = await api.getTasks(DEMO_SUBJECT_ID);
    const updated = after.ok ? after.data.find((t) => t.task_id === task!.task_id) : undefined;
    expect(updated?.version).toBe(task!.version + 1);
    expect(updated?.status).toBe('ACKNOWLEDGED');
    // 红线：确认只表达“已看到提醒”，证据状态保持 UNKNOWN，绝不推断“已吞服”。
    expect(updated?.evidence_state).toBe('UNKNOWN');
  });

  it('过期版本：expected_version 不一致返回 VERSION_CONFLICT', async () => {
    const api = new MockCoreAdapter();
    const tasks = await api.getTasks(DEMO_SUBJECT_ID);
    expect(tasks.ok).toBe(true);
    const task = tasks.ok ? tasks.data[0] : null;

    const req = makeCareRequest({
      kind: 'ACKNOWLEDGE_TASK',
      target_id: task!.task_id,
      expected_version: task!.version + 999,
    });
    const r = await api.submitRequest(DEMO_SUBJECT_ID, req);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.code).toBe('VERSION_CONFLICT');
  });
});

describe('跨主体拒绝', () => {
  it('其他 subject_id 的读与写均被拒绝', async () => {
    const api = new MockCoreAdapter();
    const other = 'subject-other-999';

    const tasks = await api.getTasks(other);
    expect(tasks.ok).toBe(false);
    if (!tasks.ok) expect(tasks.error.reason_code).toBe('SUBJECT_MISMATCH');

    const timeline = await api.getTimeline(other);
    expect(timeline.ok).toBe(false);

    const r = await api.submitRequest(other, makeCareRequest());
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.reason_code).toBe('SUBJECT_MISMATCH');
  });
});

describe('刷新恢复', () => {
  it('offline 故障清除后重取成功', async () => {
    const api = new MockCoreAdapter({ fault: 'offline' });
    expect((await api.getTasks(DEMO_SUBJECT_ID)).ok).toBe(false);

    api.setFault('none');
    expect((await api.getTasks(DEMO_SUBJECT_ID)).ok).toBe(true);
  });
});
