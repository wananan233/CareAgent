import { expect, test } from '@playwright/test';
import { SIMULATED_DATA_LABEL } from '@carehub/shared-contracts';

test.describe('适老终端壳（1024/1280 截图）', () => {
  for (const width of [1024, 1280]) {
    test(`在 ${width}px 宽度下渲染完整壳并截图`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto('/home');

      await expect(page.getByText('CareHub 老人端')).toBeVisible();
      await expect(page.getByText(SIMULATED_DATA_LABEL)).toBeVisible();
      await expect(page.locator('nav')).toBeVisible();
      await expect(page.locator('main#main-content')).toBeVisible();

      await page.screenshot({
        path: testInfo.outputPath(`shell-${width}.png`),
        fullPage: true,
      });
    });
  }
});
