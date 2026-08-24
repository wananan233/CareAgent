import { describe, expect, it } from 'vitest';
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
  makeReceipt,
} from '../builders';
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
  isRequestReceiptV1,
} from '../guards';

describe('mock builders 产出始终通过对应 guard', () => {
  it('每个 builder 的默认结果都是严格合法的', () => {
    expect(isCareEventV1(makeCareEvent())).toBe(true);
    expect(isCareTaskV1(makeCareTask())).toBe(true);
    expect(isAlertViewV1(makeAlert())).toBe(true);
    expect(isAgentResponseV1(makeAgentResponse())).toBe(true);
    expect(isConsentViewV1(makeConsent())).toBe(true);
    expect(isContextSnapshotV1(makeContextSnapshot())).toBe(true);
    expect(isDashboardViewV1(makeDashboard())).toBe(true);
    expect(isCareRequestV1(makeCareRequest())).toBe(true);
    expect(isRequestReceiptV1(makeReceipt())).toBe(true);
    expect(isErrorEnvelope(makeError('UNAVAILABLE', 'UPSTREAM_FAILED', '错误'))).toBe(true);
  });

  it('builder 支持覆盖字段且仍合法', () => {
    const task = makeCareTask({ status: 'REMINDING', evidence_state: 'UNKNOWN', version: 2 });
    expect(isCareTaskV1(task)).toBe(true);
    expect(task.status).toBe('REMINDING');
  });
});
