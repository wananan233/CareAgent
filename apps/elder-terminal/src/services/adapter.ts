import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareRequestV1,
  CareTaskV1,
  ConsentScope,
  ConsentViewV1,
  DashboardViewV1,
  ErrorEnvelope,
  RequestReceiptV1,
  SubjectId,
} from '@carehub/shared-contracts/elder';

export interface AdapterOk<T> {
  ok: true;
  data: T;
}

export interface AdapterErr {
  ok: false;
  error: ErrorEnvelope;
}

export type AdapterResult<T> = AdapterOk<T> | AdapterErr;

/**
 * 老人端统一数据访问接口（对应任务书 5 的 6 个版本化端点）。
 * MockCoreAdapter 与 CoreApiAdapter 共享的正式业务契约。
 */
export interface ElderTerminalApi {
  getDashboard(subjectId: SubjectId): Promise<AdapterResult<DashboardViewV1>>;
  getTasks(subjectId: SubjectId): Promise<AdapterResult<CareTaskV1[]>>;
  getTimeline(subjectId: SubjectId): Promise<AdapterResult<CareEventV1[]>>;
  getAlerts(subjectId: SubjectId): Promise<AdapterResult<AlertViewV1[]>>;
  submitRequest(
    subjectId: SubjectId,
    request: CareRequestV1,
  ): Promise<AdapterResult<RequestReceiptV1>>;
  chat(subjectId: SubjectId, text: string): Promise<AdapterResult<AgentResponseV1>>;
  /** Elder only consumes these two read-only BFF projections; it never calls a Provider. */
  getAgent(subjectId: SubjectId, capability: 'TODAY_STATUS' | 'DAILY_SUMMARY'): Promise<AdapterResult<AgentResponseV1>>;
  revokeConsent(subjectId: SubjectId, scope: ConsentScope): Promise<AdapterResult<ConsentViewV1>>;
}

/** 仅供开发/测试 Mock 使用；不得进入正式 Adapter 或 production bundle。 */
export interface DevelopmentFaultInjection {
  setFault(fault: 'none' | 'offline' | 'denied' | 'failed' | 'timeout'): void;
  setAgentFault(fault: 'none' | 'timeout' | 'out_of_bounds' | 'no_source'): void;
}
