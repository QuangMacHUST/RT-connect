import { expect, test } from '@playwright/test'

test('foundation route has a stable non-mock loading/error experience', async ({ page }) => {
  await page.goto('/app/system/status')
  await expect(page.getByRole('heading', { name: 'Trạng thái dịch vụ' })).toBeVisible()
  await expect(page.getByText('Nguyên tắc dữ liệu')).toBeVisible()
})
