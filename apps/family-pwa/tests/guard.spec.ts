import { describe, expect, it } from 'vitest'
import { isDashboardV1 } from '../src/contracts/guard'
import { familyDashboardFixture } from '../src/scenarios/fixtures'

describe('DashboardV1 guard', () => {
  it('accepts a complete synthetic dashboard', () => expect(isDashboardV1(familyDashboardFixture)).toBe(true))
  it('rejects an unknown data quality', () => expect(isDashboardV1({ ...familyDashboardFixture, quality: 'NORMAL' })).toBe(false))
  it('rejects a non-simulator source', () => expect(isDashboardV1({ ...familyDashboardFixture, source_refs: [{ type: 'DEVICE' }] })).toBe(false))
})
