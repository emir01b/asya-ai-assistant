import { test, expect } from '@playwright/test';

if (process.env.VOICE_TEST_BROWSER_PATH) {
  test.use({ launchOptions: { executablePath: process.env.VOICE_TEST_BROWSER_PATH } });
}

async function settings(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByRole('navigation').getByRole('button', { name: 'Ayarlar', exact: true }).click();
}

test('installed runtime is detected and install button is disabled', async ({ page }) => {
  await settings(page);
  await expect(page.getByRole('button', { name: 'Zaten kurulu', exact: true })).toBeDisabled();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test('install progress survives navigation and completion does not enable access', async ({ page }) => {
  let phase = 'not_installed';
  let posts = 0;
  await page.route('**/api/v1/agent-admin', route => route.fulfill({ json: {
    enabled: false, agents: [], scopes: [], url: 'http://127.0.0.1:8002', guide: 'http://127.0.0.1:8002/.well-known/asya-agent.json'
  } }));
  await page.route('**/api/v1/agent-admin/installation', route => {
    if (route.request().method() === 'POST') { posts++; phase = 'installing'; }
    return route.fulfill({ json: { status: phase, installed: phase === 'installed',
      progress: phase === 'installed' ? 100 : phase === 'installing' ? 30 : 0,
      message: phase === 'installing' ? 'Paketler kuruluyor.' : phase === 'installed' ? 'Kurulum tamamlandı.' : 'Henüz kurulu değil.', error: null, running: phase === 'installed' } });
  });
  await settings(page);
  await expect(page.getByRole('switch')).toBeDisabled();
  await page.getByRole('button', { name: 'Kur', exact: true }).click();
  await expect(page.getByRole('progressbar', { name: 'Ajan servisi kurulum ilerlemesi' })).toHaveAttribute('value', '30');
  await expect(page.getByRole('button', { name: 'Kuruluyor…', exact: true })).toBeDisabled();
  await page.reload();
  await page.getByRole('navigation').getByRole('button', { name: 'Ayarlar', exact: true }).click();
  await expect(page.getByRole('progressbar')).toBeVisible();
  phase = 'installed';
  await expect(page.getByRole('button', { name: 'Zaten kurulu', exact: true })).toBeDisabled();
  await expect(page.getByRole('switch')).not.toBeChecked();
  await expect(page.getByRole('switch')).toBeEnabled();
  expect(posts).toBe(1);
});

test('failed installation offers retry', async ({ page }) => {
  await page.route('**/api/v1/agent-admin/installation', route => route.fulfill({ json: {
    status: 'error', installed: false, progress: 30, message: 'Kurulum tamamlanamadı.', error: 'Bağlantıyı kontrol edin.', running: false
  } }));
  await settings(page);
  await expect(page.getByRole('button', { name: 'Tekrar dene', exact: true })).toBeEnabled();
  await expect(page.getByText('Bağlantıyı kontrol edin.', { exact: true })).toBeVisible();
});
