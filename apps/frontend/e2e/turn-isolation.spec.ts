import { test, expect, chromium } from "@playwright/test";
import path from "node:path";

test("a delayed recording upload cannot send audio into a different conversation", async () => {
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--use-file-for-fake-audio-capture=" +
        path.resolve("../../data/recordings/browser-microphone-fixture.wav"),
    ],
  });
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    permissions: ["microphone"],
  });
  const page = await context.newPage();
  const sent: { type: string }[] = [];
  page.on("websocket", (socket) =>
    socket.on("framesent", (frame) =>
      sent.push(JSON.parse(frame.payload.toString())),
    ),
  );
  let held = false;
  let release!: () => void;
  let finish!: () => void;
  const delayed = new Promise<void>((resolve) => {
    release = resolve;
  });
  const finished = new Promise<void>((resolve) => {
    finish = resolve;
  });
  // Only this browser test delays its own upload; no production API is replaced.
  await page.route("**/api/v1/audio/recordings", async (route) => {
    held = true;
    await delayed;
    try {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: "late-test-asset" }),
      });
    } catch {
      /* The conversation switch intentionally aborts this request. */
    } finally {
      finish();
    }
  });
  try {
    await page.goto("/");
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Sesli sohbet", exact: true })
      .click();
    await expect(page.getByText("Sohbet bağlı", { exact: true })).toBeVisible();
    await page
      .getByRole("button", { name: "Mikrofonu aç", exact: true })
      .click();
    await expect.poll(() => held, { timeout: 15000 }).toBe(true);
    await page
      .getByRole("button", { name: "Yeni konuşma", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Mikrofonu kapat", exact: true })
      .click();
    release();
    await finished;
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        ),
    );
    expect(sent.filter((event) => event.type === "audio")).toEqual([]);
    await expect(page.locator(".message")).toHaveCount(0);
  } finally {
    release();
    await context.close();
    await browser.close();
  }
});
