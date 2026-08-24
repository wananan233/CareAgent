import type { DashboardV1, ErrorEnvelope } from '@carehub/shared-contracts'

const quality = new Set(['VALID', 'LOW', 'CONFLICT', 'UNKNOWN'])
const consent = new Set(['ACTIVE', 'EXPIRED', 'REVOKED'])

export function isDashboardV1(value: unknown): value is DashboardV1 {
  if (typeof value !== 'object' || value === null) return false
  const data = value as Record<string, unknown>
  const member = data.family_member as Record<string, unknown> | undefined
  const consentView = data.consent as Record<string, unknown> | undefined
  return typeof data.snapshot_id === 'string' && typeof data.server_time === 'string' &&
    Array.isArray(data.source_refs) && data.source_refs.every((ref) => typeof ref === 'object' && ref !== null && (ref as Record<string, unknown>).type === 'SIMULATOR') &&
    quality.has(data.quality as string) && typeof data.last_updated_at === 'string' &&
    typeof member?.subject_id === 'string' && typeof member?.household_id === 'string' &&
    typeof member?.display_name === 'string' && typeof member?.relationship === 'string' &&
    typeof consentView?.scope === 'string' && consent.has(consentView?.status as string) &&
    typeof consentView?.expires_at === 'string' && typeof consentView?.version === 'number'
}

export function errorEnvelope(code: ErrorEnvelope['code'], message: string): ErrorEnvelope {
  return { code, message, correlation_id: crypto.randomUUID() }
}
