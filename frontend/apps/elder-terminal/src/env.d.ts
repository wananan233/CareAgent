/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Core API 基础路径（预留，未来 CoreApiAdapter 使用） */
  readonly VITE_API_BASE_URL?: string;
  /** 演示模式：mock = 使用 MockCoreAdapter（当前唯一支持值） */
  readonly VITE_DEMO_MODE?: 'mock';
}
