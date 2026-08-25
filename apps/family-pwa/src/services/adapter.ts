import type { CoreAdapter } from './CoreApiAdapter'
import { CoreApiAdapter } from './CoreApiAdapter'
import { MockCoreAdapter } from './MockCoreAdapter'

/** 页面只依赖此注入点；生产构建绝不静默回落到 Mock。 */
type RuntimeEnv = Record<string, string | boolean | undefined>
const viteEnv = (import.meta as unknown as { env: RuntimeEnv }).env
export const currentSubjectId = typeof viteEnv.VITE_CAREHUB_SUBJECT_ID === 'string' && viteEnv.VITE_CAREHUB_SUBJECT_ID ? viteEnv.VITE_CAREHUB_SUBJECT_ID : 'subject-demo-parent-01'

export function createCoreAdapter(env: RuntimeEnv = viteEnv): CoreAdapter {
  const baseUrl = env.VITE_CAREHUB_BFF_URL
  const token = env.VITE_CAREHUB_TOKEN
  const householdId = env.VITE_CAREHUB_HOUSEHOLD_ID
  if (typeof baseUrl === 'string' && typeof token === 'string' && typeof householdId === 'string' && baseUrl && token && householdId) return new CoreApiAdapter({ baseUrl, token, householdId })
  if (env.DEV === true) return new MockCoreAdapter()
  throw new Error('BFF_CONFIGURATION_REQUIRED')
}

export const coreAdapter = createCoreAdapter()
