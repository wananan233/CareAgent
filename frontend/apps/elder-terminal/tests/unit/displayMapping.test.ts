import { describe, expect, it } from 'vitest';
import {
  ACKNOWLEDGE_ACTION_LABEL,
  EVIDENCE_LABEL,
  QUALITY_LABEL,
  TASK_STATUS_LABEL,
} from '@/contracts/displayMapping';

describe('内容红线：用户确认只表达“已看到提醒”', () => {
  it('确认动作文案含“已看到”，绝不写“已吞服/已服药”', () => {
    expect(ACKNOWLEDGE_ACTION_LABEL).toContain('已看到');
    expect(ACKNOWLEDGE_ACTION_LABEL).not.toMatch(/已吞服|已服药|吞服/);
  });

  it('证据状态文案不含“已吞服/已服药”', () => {
    for (const label of Object.values(EVIDENCE_LABEL)) {
      expect(label).not.toMatch(/已吞服|已服药|吞服/);
    }
  });

  it('任务状态 ACKNOWLEDGED 只表达“已看到提醒”', () => {
    expect(TASK_STATUS_LABEL.ACKNOWLEDGED).toBe('已看到提醒');
    expect(TASK_STATUS_LABEL.ACKNOWLEDGED).not.toMatch(/已吞服|已服药/);
  });

  it('LOW/CONFLICT/UNKNOWN 质量不得显示为“正常/已完成/可信”', () => {
    for (const key of ['LOW', 'CONFLICT', 'UNKNOWN'] as const) {
      expect(QUALITY_LABEL[key]).not.toMatch(/正常|已完成|可信/);
    }
  });
});
