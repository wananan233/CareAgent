/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CAREHUB_BFF_URL?: string;
  readonly VITE_CAREHUB_TOKEN?: string;
  readonly VITE_CAREHUB_HOUSEHOLD_ID?: string;
  readonly VITE_CAREHUB_SUBJECT_ID?: string;
  /** 演示模式：mock = 使用 MockCoreAdapter。 */
  readonly VITE_DEMO_MODE?: 'mock';
}
