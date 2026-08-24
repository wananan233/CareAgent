import { expect, test } from '@playwright/test'

for (const width of [360, 390, 430]) {
  test(`F0 家属端在 ${width}px 宽度无横向溢出`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/')
    await expect(page.getByText('模拟数据 · 本地演示')).toBeVisible()
    const hasHorizontalOverflow = await page.locator('body').evaluate((body) => body.scrollWidth > window.innerWidth)
    expect(hasHorizontalOverflow).toBe(false)
    await expect(page).toHaveScreenshot(`f0-${width}.png`, { fullPage: true })
  })
}
