import { describe, expect, it } from 'vitest';
import {
  isAgentResponseV1,
  isAlertViewV1,
  isCareEventV1,
  isCareRequestV1,
  isCareTaskV1,
  isConsentViewV1,
  isContextSnapshotV1,
  isDashboardViewV1,
  isErrorEnvelope,
  isEventSource,
  safeParse,
} from '../guards';
import {
  makeAgentResponse,
  makeAlert,
  makeCareEvent,
  makeCareRequest,
  makeCareTask,
  makeConsent,
  makeContextSnapshot,
  makeDashboard,
  makeError,
} from '../builders';

describe('EventSource guard', () => {
  it('只接受 SIMULATOR 来源', () => {
    expect(isEventSource({ type: 'SIMULATOR', simulator_id: 'care-dose' })).toBe(true);
    expect(isEventSource({ type: 'REAL_DEVICE', simulator_id: 'care-dose' })).toBe(false);
    expect(isEventSource({ type: 'SIMULATOR' })).toBe(false);
  });
});

describe('CareEventV1 guard', () => {
  it('接受合法事件', () => {
    expect(isCareEventV1(makeCareEvent())).toBe(true);
  });
  it('拒绝非 SIMULATOR 来源与非法质量', () => {
    expect(isCareEventV1(makeCareEvent({ source: { type: 'SIMULATOR', simulator_id: 'x' }, quality: { status: 'REAL' as never } }))).toBe(false);
  });
  it('拒绝缺少 source_refs 的事件', () => {
    expect(isCareEventV1({ ...makeCareEvent(), source_refs: undefined })).toBe(false);
  });
});

describe('CareTaskV1 guard', () => {
  it('接受合法任务，证据状态默认可为 UNKNOWN', () => {
    expect(isCareTaskV1(makeCareTask({ evidence_state: 'UNKNOWN' }))).toBe(true);
  });
  it('拒绝非法证据状态（例如 SWALLOWED）', () => {
    expect(isCareTaskV1(makeCareTask({ evidence_state: 'SWALLOWED' as never }))).toBe(false);
  });
});

describe('AlertViewV1 guard', () => {
  it('接受 S-1/S0 告警', () => {
    expect(isAlertViewV1(makeAlert({ safety_level: 'S-1' }))).toBe(true);
    expect(isAlertViewV1(makeAlert({ safety_level: 'S0' }))).toBe(true);
  });
  it('拒绝非法安全级别', () => {
    expect(isAlertViewV1(makeAlert({ safety_level: 'S9' as never }))).toBe(false);
  });
});

describe('AgentResponseV1 guard', () => {
  it('只接受家庭端契约定义的 fallback 枚举', () => {
    expect(isAgentResponseV1(makeAgentResponse({ fallback: 'TEMPLATE_FALLBACK' }))).toBe(true);
    expect(isAgentResponseV1(makeAgentResponse({ fallback: true as never }))).toBe(false);
  });
  it('事实必须携带非空 source_refs（无来源不得成为事实）', () => {
    const noSourceFact = { text: '已吞服', source_refs: [] };
    expect(isAgentResponseV1({ ...makeAgentResponse(), facts: [noSourceFact] })).toBe(false);
  });
});

describe('Consent / Snapshot / Dashboard guards', () => {
  it('接受合法同意、快照与首页', () => {
    expect(isConsentViewV1(makeConsent())).toBe(true);
    expect(isContextSnapshotV1(makeContextSnapshot())).toBe(true);
    expect(isDashboardViewV1(makeDashboard())).toBe(true);
    expect(isDashboardViewV1(makeDashboard({ primaryTask: null }))).toBe(true);
  });
  it('拒绝 STALE 之外的 freshness', () => {
    expect(isContextSnapshotV1(makeContextSnapshot({ freshness: 'GONE' as never }))).toBe(false);
  });
});

describe('CareRequestV1 guard', () => {
  it('写请求必须携带 command_id / idempotency_key / expected_version', () => {
    expect(isCareRequestV1(makeCareRequest())).toBe(true);
    expect(isCareRequestV1({ ...makeCareRequest(), idempotency_key: '' })).toBe(false);
    expect(isCareRequestV1({ ...makeCareRequest(), expected_version: undefined })).toBe(false);
  });
});

describe('ErrorEnvelope guard', () => {
  it('接受合法错误信封，拒绝未知 reasonCode', () => {
    expect(isErrorEnvelope(makeError('OFFLINE', 'NETWORK_OFFLINE', '离线'))).toBe(true);
    expect(isErrorEnvelope(makeError('OFFLINE', 'MADE_UP' as never, '离线'))).toBe(false);
  });
});

describe('safeParse', () => {
  it('成功返回 ok:true，失败返回 ok:false 与路径', () => {
    const task = makeCareTask();
    expect(safeParse(isCareTaskV1, task)).toEqual({ ok: true, value: task });
    expect(safeParse(isCareTaskV1, {})).toMatchObject({ ok: false, path: 'value' });
  });
});
