import { CoreApiAdapter } from './CoreApiAdapter';
import { DemoAdapter } from '@carehub/mock-runtime';
import type { ElderTerminalApi } from './adapter';

type RuntimeEnv = Record<string, string | boolean | undefined>;
const viteEnv = (import.meta as unknown as { env: RuntimeEnv }).env;
export const runtimeSubjectId = typeof viteEnv.VITE_CAREHUB_SUBJECT_ID === 'string' && viteEnv.VITE_CAREHUB_SUBJECT_ID ? viteEnv.VITE_CAREHUB_SUBJECT_ID : 'subject-sim-001';

/** 开发模式仅在显式 mock 或未配置 BFF 时使用合成数据；生产构建绝不静默回落。 */
export function createElderTerminalApi(env: RuntimeEnv = viteEnv): ElderTerminalApi {
  if (env.VITE_DEMO_MODE === 'mock') return new DemoAdapter();
  const baseUrl = env.VITE_CAREHUB_BFF_URL;
  const token = env.VITE_CAREHUB_TOKEN;
  const householdId = env.VITE_CAREHUB_HOUSEHOLD_ID;
  if (typeof baseUrl === 'string' && typeof token === 'string' && typeof householdId === 'string' && baseUrl && token && householdId) {
    return new CoreApiAdapter({ baseUrl, token, householdId });
  }
  if (env.DEV === true) return new DemoAdapter();
  throw new Error('BFF_CONFIGURATION_REQUIRED');
}
