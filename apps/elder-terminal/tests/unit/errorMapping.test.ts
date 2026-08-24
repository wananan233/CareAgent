import { describe, expect, it } from 'vitest';
import type { ReasonCode } from '@carehub/shared-contracts/elder';
import { ERROR_MESSAGES, messageFor } from '@/contracts/errorMapping';

const ALL_REASON_CODES: ReasonCode[] = [
  'UNAUTHORIZED',
  'FORBIDDEN',
  'OFFLINE',
  'UNAVAILABLE',
  'INVALID_REQUEST',
  'INTERNAL_ERROR',
  'NETWORK_OFFLINE',
  'CONSENT_REVOKED',
  'CONSENT_EXPIRED',
  'SUBJECT_MISMATCH',
  'VERSION_CONFLICT',
  'UPSTREAM_TIMEOUT',
  'UPSTREAM_FAILED',
  'SCHEMA_INVALID',
  'NOT_IMPLEMENTED',
  'AGENT_FALLBACK',
];

describe('错误文案映射', () => {
  it('每个 ReasonCode 都有非空中文提示', () => {
    for (const code of ALL_REASON_CODES) {
      expect(messageFor(code).length).toBeGreaterThan(0);
    }
  });

  it('映射表与 ReasonCode 白名单一致', () => {
    expect(Object.keys(ERROR_MESSAGES).sort()).toEqual([...ALL_REASON_CODES].sort());
  });
});
