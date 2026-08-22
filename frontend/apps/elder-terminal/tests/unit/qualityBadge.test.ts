import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import QualityBadge from '@/components/QualityBadge.vue';

describe('QualityBadge 质量标识（文本 + 图标 + 颜色）', () => {
  it('VALID 显示“信息可信”', () => {
    const w = mount(QualityBadge, { props: { quality: 'VALID' } });
    expect(w.text()).toContain('信息可信');
    expect(w.find('.quality__glyph').exists()).toBe(true);
  });

  it('LOW 显示“信息待确认”并带原因', () => {
    const w = mount(QualityBadge, { props: { quality: 'LOW', reason: '活动数据不足' } });
    expect(w.text()).toContain('信息待确认');
    expect(w.text()).toContain('活动数据不足');
  });

  it('CONFLICT 显示“信息冲突”', () => {
    const w = mount(QualityBadge, { props: { quality: 'CONFLICT' } });
    expect(w.text()).toContain('信息冲突');
  });

  it('UNKNOWN 显示“暂未确认”', () => {
    const w = mount(QualityBadge, { props: { quality: 'UNKNOWN' } });
    expect(w.text()).toContain('暂未确认');
  });
});
