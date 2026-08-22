import { expect, test } from '@playwright/test';

/** 无障碍基线（U3）：单一 h1、可访问导航、按钮可访问名称、表单标签、状态不以颜色为唯一表达。 */

const STATIC_ROUTES: Array<{ path: string; title: string }> = [
  { path: '/home', title: '今日' },
  { path: '/safety', title: '安全提示' },
  { path: '/agent', title: '小护' },
  { path: '/timeline', title: '时间线' },
  { path: '/settings', title: '设置' },
  { path: '/system', title: '系统状态' },
];

test.describe('页面结构与可访问导航', () => {
  for (const { path, title } of STATIC_ROUTES) {
    test(`${path} 单一 h1 标题且导航有可访问名称`, async ({ page }) => {
      await page.goto(path);

      await expect(page.locator('h1')).toHaveCount(1);
      await expect(page.locator('h1')).toHaveText(title);
      await expect(page.locator('nav[aria-label="主导航"]')).toBeVisible();
      // 全局“模拟数据”标识与跳过链接始终存在
      await expect(page.locator('a.app-shell__skip')).toHaveCount(1);
    });
  }
});

test.describe('可访问名称', () => {
  test('所有按钮均有可访问名称（文本或 aria-label）', async ({ page }) => {
    await page.goto('/safety');
    const buttons = page.getByRole('button');
    const count = await buttons.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const btn = buttons.nth(i);
      const ariaLabel = await btn.getAttribute('aria-label');
      const text = (await btn.innerText()).trim();
      expect(ariaLabel ?? text).not.toBe('');
    }
  });

  test('表单输入有标签关联', async ({ page }) => {
    await page.goto('/agent');
    await expect(page.getByLabel('向小护提问')).toBeVisible();
  });

  test('状态不以颜色为唯一表达：离线/在线为可见文本', async ({ page }) => {
    await page.goto('/home');
    // 在线状态下文字“在线”可见（不只是彩色圆点）
    await expect(page.locator('.status-bar').getByText('在线')).toBeVisible();
  });
});
