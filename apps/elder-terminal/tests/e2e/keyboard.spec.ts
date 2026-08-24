import { expect, test } from '@playwright/test';

test.describe('键盘可访问性（Tab / 焦点 / 跳转链接）', () => {
  test('首次 Tab 聚焦跳过链接，回车后焦点进入主内容', async ({ page }) => {
    await page.goto('/home');

    await page.keyboard.press('Tab');
    const skip = page.locator('.app-shell__skip');
    await expect(skip).toBeFocused();

    await page.keyboard.press('Enter');
    await expect(page.locator('main#main-content')).toBeFocused();
  });

  test('焦点可见：聚焦元素带 focus-visible 描边', async ({ page }) => {
    await page.goto('/home');
    await page.keyboard.press('Tab');
    const skip = page.locator('.app-shell__skip');
    const outline = await skip.evaluate((el) => {
      const s = getComputedStyle(el);
      return { width: s.outlineWidth, style: s.outlineStyle };
    });
    expect(parseFloat(outline.width)).toBeGreaterThan(0);
    expect(outline.style).not.toBe('none');
  });
});
