import { describe, expect, it } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { isAgentResponseV1 } from '@carehub/shared-contracts';
import AgentPage from '@/pages/AgentPage.vue';
import { useCareStore } from '@/stores/care';
import { fixtureAgentNoSource } from '@/scenarios/fixtures';
import { AGENT_FAILURE_LABEL } from '@/contracts/displayMapping';
import type { AgentFault } from '@/services/MockCoreAdapter';

function setup(agentFault?: AgentFault) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const care = useCareStore();
  if (agentFault) care.api.setAgentFault(agentFault);
  const wrapper = mount(AgentPage, { global: { plugins: [pinia] } });
  return { care, wrapper };
}

describe('Agent 页（小护）', () => {
  it('正常回复展示 AI 身份标识与来源抽屉', async () => {
    const { care, wrapper } = setup();
    await care.askAgent('今天要做什么？');
    await flushPromises();

    expect(wrapper.text()).toContain('AI 生成');
    expect(wrapper.text()).toContain('今日提醒已整理完毕。');

    const toggle = wrapper.find('.source-drawer__toggle');
    expect(toggle.exists()).toBe(true);
    await toggle.trigger('click');
    expect(wrapper.text()).toContain('CareDose 合成事件');
  });

  it('越界回复降级为安全回退模板（不渲染原始模型文本）', async () => {
    const { care, wrapper } = setup('out_of_bounds');
    await care.askAgent('请给我一个诊断');
    await flushPromises();

    expect(wrapper.text()).toContain('助手暂时无法给出解释');
    expect(wrapper.text()).not.toContain('AI 生成');
  });

  it('无来源事实：guard 拒绝并显示模板失败态，绝不渲染原始模型文本', async () => {
    const { care, wrapper } = setup('no_source');
    await care.askAgent('你吃药了吗');
    await flushPromises();

    expect(wrapper.text()).toContain(AGENT_FAILURE_LABEL);
    expect(wrapper.text()).not.toContain('已按医嘱服药');
    expect(wrapper.text()).not.toContain('原始模型文本');
  });

  it('模型超时返回失败态', async () => {
    const { care, wrapper } = setup('timeout');
    await care.askAgent('你好');
    await flushPromises();

    expect(wrapper.text()).toContain('暂时无法回答');
    expect(wrapper.text()).toContain('服务响应超时');
  });
});

describe('Agent guard 校验', () => {
  it('无来源事实的回复不通过 isAgentResponseV1', () => {
    expect(isAgentResponseV1(fixtureAgentNoSource())).toBe(false);
  });

  it('no_source 下 store 不缓存原始回复，agentError=SCHEMA_INVALID', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const care = useCareStore();
    care.api.setAgentFault('no_source');

    await care.askAgent('你吃药了吗');
    expect(care.agent).toBeNull();
    expect(care.agentError).toBe('SCHEMA_INVALID');
  });
});
