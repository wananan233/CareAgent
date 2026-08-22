import { makeError } from '@carehub/shared-contracts';
import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareRequestV1,
  CareTaskV1,
  ConsentScope,
  ConsentViewV1,
  DashboardViewV1,
  RequestReceiptV1,
  SubjectId,
} from '@carehub/shared-contracts';
import type { AdapterResult, ElderTerminalApi } from './adapter';

/**
 * 真实 BFF 适配器（C0-C4 就绪前的占位实现）。
 *
 * 与 MockCoreAdapter 共享同一 ElderTerminalApi 契约。当前所有端点返回
 * NOT_IMPLEMENTED，明确表示“OpenAPI 声明 ≠ 已运行接口”。真实 HTTP 接入
 * 需等 C2 BFF 完成，属后续阶段工作，本阶段不实现。
 */
export class CoreApiAdapter implements ElderTerminalApi {
  private notImplemented(): AdapterResult<never> {
    return {
      ok: false,
      error: makeError('NOT_IMPLEMENTED', 'NOT_IMPLEMENTED', '该接口尚未接入', false),
    };
  }

  async getDashboard(_subjectId: SubjectId): Promise<AdapterResult<DashboardViewV1>> {
    return this.notImplemented();
  }

  async getTasks(_subjectId: SubjectId): Promise<AdapterResult<CareTaskV1[]>> {
    return this.notImplemented();
  }

  async getTimeline(_subjectId: SubjectId): Promise<AdapterResult<CareEventV1[]>> {
    return this.notImplemented();
  }

  async getAlerts(_subjectId: SubjectId): Promise<AdapterResult<AlertViewV1[]>> {
    return this.notImplemented();
  }

  async submitRequest(
    _subjectId: SubjectId,
    _request: CareRequestV1,
  ): Promise<AdapterResult<RequestReceiptV1>> {
    return this.notImplemented();
  }

  async chat(_subjectId: SubjectId, _text: string): Promise<AdapterResult<AgentResponseV1>> {
    return this.notImplemented();
  }

  async revokeConsent(
    _subjectId: SubjectId,
    _scope: ConsentScope,
  ): Promise<AdapterResult<ConsentViewV1>> {
    return this.notImplemented();
  }
}
