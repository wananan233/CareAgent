import { CoreApiAdapter } from './CoreApiAdapter';
import { MockCoreAdapter } from './MockCoreAdapter';
import type { ElderTerminalApi } from './adapter';

type RuntimeEnv = Record<string, string | boolean | undefined>;
const viteEnv = (import.meta as unknown as { env: RuntimeEnv }).env;

/** 开发模式仅在显式 mock 或未配置 BFF 时使用合成数据；生产构建绝不静默回落。 */
export function createElderTerminalApi(env: RuntimeEnv = viteEnv): ElderTerminalApi {
  if (env.VITE_DEMO_MODE === 'mock') return new MockCoreAdapter();
  const baseUrl = env.VITE_CAREHUB_BFF_URL;
  const token = env.VITE_CAREHUB_TOKEN;
  const householdId = env.VITE_CAREHUB_HOUSEHOLD_ID;
  if (typeof baseUrl === 'string' && typeof token === 'string' && typeof householdId === 'string' && baseUrl && token && householdId) {
    return new CoreApiAdapter({ baseUrl, token, householdId });
  }
  if (env.DEV === true) return new MockCoreAdapter();
  throw new Error('BFF_CONFIGURATION_REQUIRED');
}
