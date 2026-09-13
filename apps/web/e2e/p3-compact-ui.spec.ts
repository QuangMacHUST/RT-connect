import { expect, test } from '@playwright/test'

for (const viewport of [
  { name: 'máy tính tiêu chuẩn', width: 1366, height: 768 },
  { name: 'màn hình rộng', width: 1440, height: 900 }
]) {
  test(`luồng đăng nhập gọn trong một màn hình — ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/auth/login')

    await expect(page.getByRole('heading', { name: 'Đăng nhập RT-CONNECT' })).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Mật khẩu')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Trạng thái dịch vụ' })).toBeVisible()
    await expect(page.locator('body')).not.toContainText('MOD-')

    const fitsViewport = await page.evaluate(() => document.documentElement.scrollHeight <= window.innerHeight + 4)
    expect(fitsViewport).toBe(true)
  })
}
