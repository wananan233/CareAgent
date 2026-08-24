import { expect, test } from '@playwright/test';

/**
 * 五条必须闭环的演示场景（任务书 3.2）。
 * 每个场景从合成事件到页面再到 Core 请求端到端运行，并截图留证。
 */

test.describe('场景 1 · CareDose 服药提醒闭环', () => {
  test('主任务 → 详情 → 我已看到提醒 → 证据仍 UNKNOWN', async ({ page }, testInfo) => {
    await page.goto('/home');

    // 首页出现一个主任务
    await expect(page.getByRole('heading', { name: '按时服药' })).toBeVisible();
    await expect(page.getByText('模拟数据')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('1a-home.png'),
      fullPage: true,
    });

    // 进入详情
    await page.getByRole('link', { name: '查看任务详情' }).click();
    await expect(page).toHaveURL(/\/task\//);
    await expect(page.getByText('证据状态')).toBeVisible();

    // 提交确认请求
    await page.getByRole('button', { name: '我已看到提醒' }).click();
    await expect(page.getByText('确认请求已接收')).toBeVisible();

    // 证据仍 UNKNOWN，绝不显示“已吞服”
    await expect(page.getByText('已确认看到提醒，证据状态仍为')).toBeVisible();
    await expect(page.getByText('已吞服')).toHaveCount(0);

    await page.screenshot({
      path: testInfo.outputPath('1b-task-detail.png'),
      fullPage: true,
    });
  });
});

test.describe('场景 2 · CareSafe 烟雾/燃气安全告警', () => {
  test('不可忽略安全卡 → 安全页 → 查看时间与来源 → 无关闭/取消', async ({ page }, testInfo) => {
    await page.goto('/home');

    // 任意页面出现不可忽略安全卡
    await expect(page.locator('.global-safety')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('2a-global-safety.png'),
      fullPage: true,
    });

    // 进入安全页
    await page.getByRole('link', { name: '安全提示' }).click();
    await expect(page).toHaveURL(/\/safety/);
    await expect(page.locator('.alert-card')).toHaveCount(2);
    await expect(page.locator('.alert-card').filter({ hasText: 'S-1' })).toContainText('烟雾/燃气');

    // S-1/S0 卡片不提供关闭/取消
    await expect(page.getByRole('button', { name: /关闭|取消/ })).toHaveCount(0);

    // 查看详情：发生时间与来源
    await page.locator('.alert-card').first().getByRole('link', { name: '查看详情' }).click();
    await expect(page).toHaveURL(/\/alert\//);
    await expect(page.getByText('发生时间')).toBeVisible();
    await expect(page.getByText('模拟数据（SIMULATOR）')).toBeVisible();
    await expect(page.getByRole('button', { name: /关闭|取消/ })).toHaveCount(0);

    await page.screenshot({
      path: testInfo.outputPath('2b-alert-detail.png'),
      fullPage: true,
    });
  });
});

test.describe('场景 3 · CareRadar 低质量活动数据', () => {
  test('今日页活动待确认 → 时间线 quality 原因', async ({ page }, testInfo) => {
    await page.goto('/home');

    // 今日页只展示家庭端契约允许的 MEDICATION_DUE 任务，证据仍为 UNKNOWN
    await expect(page.getByRole('heading', { name: '按时服药' })).toBeVisible();
    await expect(page.getByRole('link', { name: /按时服药/ })).toContainText('暂未确认');

    // 时间线看到 LOW 质量原因
    await page.getByRole('link', { name: '时间线' }).click();
    await expect(page).toHaveURL(/\/timeline/);
    await expect(page.getByText('活动数据待确认')).toBeVisible();
    await expect(page.getByText('信息待确认')).toBeVisible();
    await expect(page.getByText('活动数据不足，暂未确认')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('3-timeline.png'),
      fullPage: true,
    });
  });
});

test.describe('场景 4 · CareAgent DAILY_SUMMARY', () => {
  test('逐条展示事实与来源，AI 身份标识可见', async ({ page }, testInfo) => {
    await page.goto('/agent');

    await page.getByLabel('向小护提问').fill('今天要做什么？');
    await page.getByRole('button', { name: '提问' }).click();

    // AI 身份 + 摘要 + 事实
    await expect(page.getByText('AI 生成')).toBeVisible();
    await expect(page.getByText('今日提醒已整理完毕。')).toBeVisible();
    await expect(page.getByText('上午的服药提醒已由系统生成。')).toBeVisible();

    // 与家庭端相同的字符串来源引用
    await expect(page.getByText('来源：evt-medication-001')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('4-agent.png'),
      fullPage: true,
    });
  });
});

test.describe('场景 5 · 网络断开与离线壳', () => {
  test('离线条出现，低风险待重新提交，高风险阻断', async ({ page }, testInfo) => {
    await page.goto('/home');
    await expect(page.getByRole('heading', { name: '按时服药' })).toBeVisible();

    // 进入系统页模拟离线
    await page.getByRole('link', { name: '系统状态' }).click();
    await expect(page).toHaveURL(/\/system/);
    await page.getByRole('button', { name: '模拟离线' }).click();

    // 离线条出现
    await expect(page.locator('.status-bar').getByText('离线')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('5a-offline.png'),
      fullPage: true,
    });

    // 低风险请求：只显示“待网络恢复后重新提交”，不自动执行
    await page.getByRole('link', { name: '今日' }).click();
    await page.getByRole('link', { name: '查看任务详情' }).click();
    await page.getByRole('button', { name: '我已看到提醒' }).click();
    await expect(page.getByText('待网络恢复后重新提交')).toBeVisible();
    // 任务未被确认，仍为“待处理”
    await expect(page.getByText('待处理')).toBeVisible();

    // 高风险请求：安全告警确认被阻断，不进入队列
    await page.getByRole('link', { name: '安全提示' }).click();
    await page.locator('.alert-card').first().getByRole('link', { name: '查看详情' }).click();
    await page.getByRole('button', { name: '我已看到提醒' }).click();
    await expect(page.getByText('离线时无法执行此操作')).toBeVisible();

    await page.screenshot({
      path: testInfo.outputPath('5b-blocked.png'),
      fullPage: true,
    });
  });
});
