import { expect, test } from '@playwright/test';

async function fontSize(locator: import('@playwright/test').Locator): Promise<number> {
  return locator.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
}

test.describe('适老排版红线（正文≥20px / 主任务≥30px / 按钮≥56px）', () => {
  test('首页正文、主任务、主按钮满足字号与触控底线', async ({ page }) => {
    await page.goto('/home');

    const welcome = page.locator('.home__welcome');
    await expect(welcome).toBeVisible();
    expect(await fontSize(welcome)).toBeGreaterThanOrEqual(20);

    const mainTask = page.locator('.main-task__kind');
    await expect(mainTask).toBeVisible();
    expect(await fontSize(mainTask)).toBeGreaterThanOrEqual(30);

    const action = page.locator('.main-task__action');
    await expect(action).toBeVisible();
    const box = await action.boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(56);
  });

  test('导航链接触控目标 ≥ 56px', async ({ page }) => {
    await page.goto('/home');
    const firstNav = page.locator('nav .nav__link').first();
    await expect(firstNav).toBeVisible();
    const box = await firstNav.boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(56);
  });
});
