import { describe, expect, it } from 'vitest';
import {
  fixtureAgentResponse,
  fixtureLowQualityEvent,
  fixtureMedicationTask,
  fixtureSmokeGasAlert,
} from '@/scenarios/fixtures';

describe('合成 fixtures 内容红线', () => {
  it('用药任务证据状态为 UNKNOWN，绝不表达“已吞服/已服药”', () => {
    const t = fixtureMedicationTask();
    expect(t.evidenceState).toBe('UNKNOWN');
    expect(t.status).toBe('DUE');
  });

  it('低质量活动事件的来源为 SIMULATOR 且质量为 LOW', () => {
    const e = fixtureLowQualityEvent();
    expect(e.source.type).toBe('SIMULATOR');
    expect(e.quality.status).toBe('LOW');
  });

  it('安全告警为 S0 且状态由服务端决定（ACTIVE）', () => {
    const a = fixtureSmokeGasAlert();
    expect(a.safetyLevel).toBe('S0');
    expect(a.status).toBe('ACTIVE');
  });

  it('Agent 每日摘要的每条事实都携带非空来源', () => {
    const r = fixtureAgentResponse();
    expect(r.fallback).toBe(false);
    expect(r.facts.every((f) => f.sourceRefs.length > 0)).toBe(true);
  });
});
