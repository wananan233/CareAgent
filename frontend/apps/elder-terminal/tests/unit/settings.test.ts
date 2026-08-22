import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import SettingsPage from '@/pages/SettingsPage.vue';
import { useAppStore } from '@/stores/app';

function setup() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(SettingsPage, { global: { plugins: [pinia] } });
  return { app: useAppStore(), wrapper };
}

describe('设置页（字号/声音/提醒 + 恢复默认）', () => {
  it('点击“最大”字号更新 store.fontScale', async () => {
    const { app, wrapper } = setup();
    const buttons = wrapper.findAll('.settings__option');
    await buttons.find((b) => b.text() === '最大')!.trigger('click');
    expect(app.fontScale).toBe(1.5);
  });

  it('恢复默认将字号/声音/提醒还原', async () => {
    const { app, wrapper } = setup();
    app.setFontScale(1.5);
    app.setSoundEnabled(true);
    app.setNonCriticalReminders(false);

    await wrapper.find('.settings__restore').trigger('click');
    expect(app.fontScale).toBe(1);
    expect(app.soundEnabled).toBe(false);
    expect(app.nonCriticalReminders).toBe(true);
  });
});
