import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import StateView from '@/components/StateView.vue';

describe('StateView 状态视图（文本 + 图标 + 颜色 + role=status）', () => {
  const variants = [
    { variant: 'loading', title: '加载中…' },
    { variant: 'empty', title: '暂无内容' },
    { variant: 'denied', title: '暂无权限' },
    { variant: 'offline', title: '当前离线' },
  ] as const;

  for (const { variant, title } of variants) {
    it(`渲染 ${variant} 变体：标题 + 图标 + status 语义`, () => {
      const wrapper = mount(StateView, { props: { variant, title } });
      expect(wrapper.find('[role="status"]').exists()).toBe(true);
      expect(wrapper.text()).toContain(title);
      expect(wrapper.find('.state-view__icon').exists()).toBe(true);
    });
  }

  it('带可选描述文字', () => {
    const wrapper = mount(StateView, {
      props: { variant: 'offline', title: '当前离线', description: '网络恢复后将自动更新。' },
    });
    expect(wrapper.text()).toContain('网络恢复后将自动更新。');
  });
});
