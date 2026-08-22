import { describe, expect, it } from 'vitest';
import { tokens } from '@/tokens';

describe('适老设计 token（任务书 3.1 P0）', () => {
  it('正文 >= 20px、主要任务 >= 30px、数字时间 >= 28px', () => {
    expect(tokens.fontSize.body).toBeGreaterThanOrEqual(20);
    expect(tokens.fontSize.main).toBeGreaterThanOrEqual(30);
    expect(tokens.fontSize.time).toBeGreaterThanOrEqual(28);
  });

  it('主要触控目标 >= 56px', () => {
    expect(tokens.touch.minTarget).toBeGreaterThanOrEqual(56);
  });

  it('关键动作字号（caption）不得小于 20px', () => {
    expect(tokens.fontSize.caption).toBeGreaterThanOrEqual(20);
  });
});
