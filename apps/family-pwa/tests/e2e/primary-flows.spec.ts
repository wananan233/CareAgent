import { expect, test } from '@playwright/test'

test('五个主导航进入真实功能页面', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('link', { name: '提醒', exact: true }).click()
  await expect(page.getByRole('heading', { name: '提醒', exact: true })).toBeVisible()
  await expect(page.getByText('证据状态')).toBeVisible()
  await page.getByRole('link', { name: '关怀', exact: true }).click()
  await expect(page.getByRole('heading', { name: '关怀', exact: true })).toBeVisible()
  await page.getByRole('button', { name: /关怀问候/ }).click()
  await page.getByRole('button', { name: '确认提交' }).click()
  await expect(page.getByText('请求已记录')).toBeVisible()
  await page.getByRole('link', { name: '报告', exact: true }).click()
  await expect(page.getByText('来源与质量')).toBeVisible()
  await page.getByRole('link', { name: '我的', exact: true }).click()
  await expect(page.getByText('隐私与授权')).toBeVisible()
})

test('安全告警只能记录已查看，不能解除', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/alerts/alert-smoke-gas-001')
  await expect(page.getByText('告警仍处于开放状态')).toBeVisible()
  await page.getByRole('button', { name: '记录我已查看' }).click()
  await expect(page.getByText('已查看请求已记录')).toBeVisible()
  await expect(page.getByText('告警仍由 Core 管理')).toBeVisible()
  await expect(page.getByRole('button', { name: /解除|取消/ })).toHaveCount(0)
})
