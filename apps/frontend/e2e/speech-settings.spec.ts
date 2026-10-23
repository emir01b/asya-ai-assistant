import { test, expect } from "@playwright/test";

test("chat speech rate is editable, saved and restored after a reload", async ({
  page,
  request,
}) => {
  const original = await (await request.get("/api/v1/settings")).json();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const openSettings = async () => {
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Ayarlar", exact: true })
      .click();
  };
  try {
    await page.goto("/");
    await openSettings();
    const speed = page.getByRole("slider", { name: "Sohbet konuşma hızı" });
    await expect(speed).toHaveValue(String(original.chat_speech_rate));
    await speed.focus();
    await speed.press("Home");
    await speed.press("ArrowRight");
    await speed.press("ArrowRight");
    await expect(speed).toHaveValue("0.85");
    const saved = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/settings") && r.request().method() === "PUT",
    );
    await page
      .getByRole("button", { name: "Ayarları kaydet", exact: true })
      .click();
    expect((await saved).ok()).toBe(true);
    await page.reload();
    await openSettings();
    await expect(speed).toHaveValue("0.85");
    await expect(page.getByLabel("SİSTEM PROMPT’U")).toHaveValue(
      original.system_prompt,
    );
    await page.screenshot({
      path: "../../docs/streaming-speech-settings.png",
      fullPage: true,
    });
    expect(errors).toEqual([]);
  } finally {
    const restored = await request.put("/api/v1/settings", { data: original });
    expect(restored.ok()).toBe(true);
  }
});
