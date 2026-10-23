import { test, expect, chromium } from "@playwright/test";
import path from "node:path";

test("all seven pages use live backend and responsive layout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Sözcüklerinize ses verin." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Ses oluştur", exact: true }),
  ).toBeDisabled();
  await page.screenshot({
    path: "../../docs/studio-desktop.png",
    fullPage: true,
  });
  const pages = [
    ["Genel bakış", "Her şey, tek bir stüdyoda."],
    ["Ses kütüphanesi", "Her sesin bir karakteri var."],
    ["Üretim geçmişi", "Ürettiğiniz her ses burada."],
    ["Tanılama", "Tahmin değil, ölçüm."],
    ["Ayarlar", "Stüdyonuz, sizin ayarlarınız."],
    ["Sesli sohbet", "Konuşmak kadar doğal."],
  ];
  for (const [name, title] of pages) {
    await page
      .getByRole("navigation")
      .getByRole("button", { name, exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Ses Stüdyosu", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("textbox", { name: "Seslendirilecek metin" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../docs/studio-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("reference upload, real GPU voice generation, playback and history", async ({
  page,
}) => {
  const profileName = "Tarayıcı sesi " + Date.now();
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Ses kütüphanesi", exact: true })
    .click();
  await page.getByLabel("PROFİL ADI", { exact: true }).fill(profileName);
  await page
    .getByLabel("Referans ses dosyası", { exact: true })
    .setInputFiles(path.resolve("../../chatterbox/referans_pcm.wav"));
  await page
    .getByLabel("Bu sesin hak sahibiyim veya kullanım iznim var.")
    .check();
  await page.getByRole("button", { name: "Profili oluştur" }).click();
  await expect(
    page.getByRole("heading", { name: profileName, exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Ses Stüdyosu", exact: true })
    .click();
  await page
    .getByLabel("Seslendirilecek metin")
    .fill("Merhaba, bu stüdyoda Türkçe konuşabiliyorum.");
  await page
    .getByLabel("Ses profili", { exact: true })
    .selectOption({ label: profileName });
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/v1/tts/generate") && r.status() === 202,
  );
  await page.getByRole("button", { name: "Ses oluştur", exact: true }).click();
  const job = await (await response).json();
  await expect(page.getByText("Üretilen ses", { exact: true })).toBeVisible({
    timeout: 80000,
  });
  const audio = page.locator("audio").first();
  await expect(audio).toHaveAttribute("src", /api\/v1\/audio/);
  await audio.evaluate(async (element) => {
    const a = element as HTMLAudioElement;
    await a.play();
  });
  await expect
    .poll(() => audio.evaluate((e) => (e as HTMLAudioElement).currentTime))
    .toBeGreaterThan(0);
  const result = await page.request.get(`/api/v1/tts/jobs/${job.id}`);
  const record = await result.json();
  expect(record.status).toBe("completed");
  expect(record.metrics.duration).toBeGreaterThan(0);
  await page.screenshot({
    path: "../../docs/studio-generated.png",
    fullPage: true,
  });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Üretim geçmişi", exact: true })
    .click();
  await expect(
    page
      .getByRole("heading", {
        name: "Merhaba, bu stüdyoda Türkçe konuşabiliyorum.",
        exact: true,
      })
      .first(),
  ).toBeVisible();
});

test("STT upload returns actual Turkish transcript", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Tanılama", exact: true })
    .click();
  await page
    .getByLabel("Transkripsiyon dosyası")
    .setInputFiles(path.resolve("../../chatterbox/referans_pcm.wav"));
  await page
    .getByRole("button", { name: "Yazıya dönüştür", exact: true })
    .click();
  await expect(page.locator(".transcript strong")).not.toBeEmpty({
    timeout: 80000,
  });
  await expect(page.locator(".transcript")).toContainText("cuda");
});

test("microphone permission denial is shown", async ({ page, context }) => {
  await context.clearPermissions();
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException("Permission denied", "NotAllowedError");
    };
  });
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Sesli sohbet", exact: true })
    .click();
  await expect(page.getByText("Sohbet bağlı", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Mikrofonu aç", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Mikrofon açılamadı");
});

test("continuous PCM microphone completes consecutive voice replies without noise interruptions", async () => {
  test.setTimeout(150000);
  const fixture = path.resolve(
    "../../data/recordings/browser-microphone-fixture.wav",
  );
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--use-file-for-fake-audio-capture=" + fixture,
    ],
  });
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    ignoreHTTPSErrors: test.info().project.use.ignoreHTTPSErrors,
    permissions: ["microphone"],
  });
  const page = await context.newPage();
  const events: { type: string; [key: string]: unknown }[] = [];
  const sent: { type: string }[] = [];
  page.on("websocket", (socket) =>
    socket.on("framereceived", (frame) =>
      events.push(JSON.parse(frame.payload.toString())),
    ),
  );
  page.on("websocket", (socket) =>
    socket.on("framesent", (frame) =>
      sent.push(JSON.parse(frame.payload.toString())),
    ),
  );
  await page.addInitScript(() => {
    (
      window as Window & { verifiedAudioPlayback?: number }
    ).verifiedAudioPlayback = 0;
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      return play.call(this).then(() => {
        const target = window as Window & { verifiedAudioPlayback?: number };
        target.verifiedAudioPlayback = (target.verifiedAudioPlayback || 0) + 1;
      });
    };
  });
  try {
    await page.goto("/");
    const lm = await (await page.request.get("/api/v1/llm/status")).json();
    const settings = await (await page.request.get("/api/v1/settings")).json();
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Sesli sohbet", exact: true })
      .click();
    await expect(page.getByText("Sohbet bağlı", { exact: true })).toBeVisible();
    await page
      .getByRole("button", { name: "Mikrofonu aç", exact: true })
      .click();
    await expect(page.locator(".message.user p").first()).toContainText(
      "Türkçe",
      { timeout: 60000 },
    );
    if (lm.connected && settings.llm_model) {
      await expect(
        page.getByLabel("Konuşarak araya gir", { exact: true }),
      ).not.toBeChecked();
      await expect
        .poll(() => events.some((e) => e.type === "done"), { timeout: 80000 })
        .toBe(true);
      expect(events.some((e) => e.type === "token")).toBe(true);
      expect(events.some((e) => e.type === "audio")).toBe(true);
      expect(events.filter((e) => e.type === "error")).toEqual([]);
      await expect(
        page.locator(".message.assistant p").first(),
      ).not.toBeEmpty();
      await page
        .getByRole("button", { name: "Ses kuyruğunu oynat", exact: true })
        .click();
      await expect
        .poll(() =>
          page.evaluate(
            () =>
              (window as Window & { verifiedAudioPlayback?: number })
                .verifiedAudioPlayback || 0,
          ),
        )
        .toBeGreaterThan(0);
      await expect
        .poll(() => events.filter((e) => e.type === "done").length, {
          timeout: 80000,
        })
        .toBeGreaterThanOrEqual(2);
      await page
        .getByRole("button", { name: "Mikrofonu kapat", exact: true })
        .click();
      expect(sent.filter((e) => e.type === "interrupt")).toEqual([]);
      expect(events.filter((e) => e.type === "error")).toEqual([]);
      for (const event of events.filter((e) => e.type === "done"))
        expect((event.message as { interrupted: boolean }).interrupted).toBe(
          false,
        );
      await page.screenshot({
        path: "../../docs/live-voice-chat.png",
        fullPage: true,
      });
    } else {
      await page
        .getByRole("button", { name: "Mikrofonu kapat", exact: true })
        .click();
      await expect(page.getByRole("alert")).toContainText(/LM Studio|model/);
    }
  } finally {
    await context.close();
    await browser.close();
  }
});
