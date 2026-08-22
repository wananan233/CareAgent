import { expect, test } from '@playwright/test';

test.describe('字号缩放设置', () => {
  test('选择“最大”档位后正文字号变大且 CSS 变量更新', async ({ page }) => {
    await page.goto('/settings');

    const preview = page.locator('.settings__preview');
    const before = parseFloat(await preview.evaluate((el) => getComputedStyle(el).fontSize));

    await page.getByRole('button', { name: '最大' }).click();

    const after = parseFloat(await preview.evaluate((el) => getComputedStyle(el).fontSize));
    expect(after).toBeGreaterThan(before);

    const scale = await page.evaluate(() =>
      document.documentElement.style.getPropertyValue('--font-scale'),
    );
    expect(scale).toBe('1.5');
  });

  test('恢复默认还原为 1 倍字号', async ({ page }) => {
    await page.goto('/settings');
    await page.getByRole('button', { name: '最大' }).click();
    await page.getByRole('button', { name: '恢复默认设置' }).click();

    const scale = await page.evaluate(() =>
      document.documentElement.style.getPropertyValue('--font-scale'),
    );
    expect(scale).toBe('1');
  });
});
