import { test, expect } from '@playwright/test';

if (process.env.VOICE_TEST_BROWSER_PATH) {
  test.use({ launchOptions: { executablePath: process.env.VOICE_TEST_BROWSER_PATH } });
}

test('agent access defaults off and settings layout is usable', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation').getByRole('button', { name: 'Ayarlar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ajan erişimi', exact: true })).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Ajan erişimine izin ver' })).not.toBeChecked();
  await expect(page.getByLabel('AJAN ADI', { exact: true })).toBeVisible();
  await page.getByText('Ek izinler (isteğe bağlı)', { exact: true }).click();
  await expect(page.getByLabel('Sesi yazıya çevirme', { exact: true })).not.toBeChecked();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
