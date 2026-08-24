import { describe, expect, it } from 'vitest';
import { PAGE_STATE_MATRIX } from '@/contracts/stateMatrix';

const REQUIRED_ROUTES = [
  '/home',
  '/task/:id',
  '/safety',
  '/agent',
  '/timeline',
  '/settings',
  '/system',
];

describe('页面状态矩阵（U0 证据）', () => {
  it('覆盖全部 7 个页面路由', () => {
    const routes = PAGE_STATE_MATRIX.map((r) => r.route);
    for (const r of REQUIRED_ROUTES) {
      expect(routes).toContain(r);
    }
  });

  it('每个页面都声明了允许状态与禁止行为', () => {
    for (const rule of PAGE_STATE_MATRIX) {
      expect(rule.states.length).toBeGreaterThan(0);
      expect(rule.forbidden.length).toBeGreaterThan(0);
    }
  });

  it('安全页禁止取消 S-1/S0（不可前端取消）', () => {
    const safety = PAGE_STATE_MATRIX.find((r) => r.route === '/safety');
    expect(safety?.forbidden).toContain('S-1/S0');
  });

  it('任务页禁止把 UNKNOWN 显示为已完成', () => {
    const task = PAGE_STATE_MATRIX.find((r) => r.route === '/task/:id');
    expect(task?.forbidden).toContain('UNKNOWN');
  });

  it('系统页禁止将陈旧缓存标作实时状态', () => {
    const system = PAGE_STATE_MATRIX.find((r) => r.route === '/system');
    expect(system?.forbidden).toContain('陈旧');
  });
});
