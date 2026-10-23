import { test, expect } from "@playwright/test";

test("LAN written chat receives a real LM Studio reply", async ({ page }) => {
  let conversationId = "";
  const events: { type: string; conversation_id?: string }[] = [];
  page.on("websocket", (socket) =>
    socket.on("framereceived", (frame) => {
      const event = JSON.parse(frame.payload.toString());
      events.push(event);
      if (event.type === "start") conversationId = event.conversation_id;
    }),
  );
  await page.goto("/");
  const lm = await (await page.request.get("/api/v1/llm/status")).json();
  test.skip(!lm.connected, "LM Studio required for live chat verification");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Sesli sohbet", exact: true })
    .click();
  await page.getByLabel("Sesli yanıt", { exact: true }).uncheck();
  await page
    .getByRole("textbox", { name: "Sohbet mesajı" })
    .fill(
      "Bu bir yerel ağ bağlantı testidir. Türkçe tek kısa cümle ile merhaba de.",
    );
  await page.getByRole("button", { name: "Mesaj gönder", exact: true }).click();
  await expect
    .poll(() => events.some((event) => event.type === "done"), {
      timeout: 45000,
    })
    .toBe(true);
  await expect(page.locator(".message.assistant p").first()).not.toBeEmpty();
  expect(events.filter((event) => event.type === "error")).toEqual([]);
  expect(conversationId).not.toBe("");
  expect(
    (await page.request.delete(`/api/v1/conversations/${conversationId}`)).ok(),
  ).toBe(true);
});

// Run against the actual LAN listener with VOICE_TEST_BASE_URL=http://<ip>:8000.
test.beforeEach(async ({ baseURL }) => {
  test.skip(
    !baseURL || ["localhost", "127.0.0.1"].includes(new URL(baseURL).hostname),
    "LAN URL required",
  );
});

test("LAN settings report the live server address", async ({
  page,
  request,
  baseURL,
}) => {
  const health = await request.get("/api/v1/health");
  expect(health.ok()).toBe(true);
  const status = await (await request.get("/api/v1/system/status")).json();
  expect(status.network.lan_enabled).toBe(true);
  const isHttps = baseURL?.startsWith("https:");
  expect(isHttps ? status.network.https_url : status.network.lan_url).toBe(
    baseURL,
  );
  await page.goto("/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Ayarlar", exact: true })
    .click();
  await expect(
    page.getByText("Localhost ve yerel ağ", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      isHttps ? `HTTPS adresi: ${baseURL}` : `Yerel ağ adresi: ${baseURL}`,
      { exact: true },
    ),
  ).toBeVisible();
});

test("LAN voice socket works and microphone matches page security", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  const event = await page.evaluate(
    () =>
      new Promise<{ state: string }>((resolve, reject) => {
        const ws = new WebSocket(
          `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/v1/realtime/voice`,
        );
        const timer = setTimeout(() => {
          ws.close();
          reject(new Error("LAN WebSocket timeout"));
        }, 5000);
        ws.onopen = () => ws.send(JSON.stringify({ type: "interrupt" }));
        ws.onmessage = (message) => {
          clearTimeout(timer);
          ws.close();
          resolve(JSON.parse(message.data));
        };
        ws.onerror = () => {
          clearTimeout(timer);
          ws.close();
          reject(new Error("LAN WebSocket failed"));
        };
      }),
  );
  expect(event.state).toBe("interrupted");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Sesli sohbet", exact: true })
    .click();
  if (new URL(page.url()).protocol === "http:") {
    await page
      .getByRole("button", { name: "Mikrofonu aç", exact: true })
      .click();
    await expect(
      page.getByText(/Yerel ağda mikrofon kullanmak için HTTPS gerekir/),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Yerel sertifikayı indir", exact: true }),
    ).toBeVisible();
  } else {
    expect(
      await page.evaluate(
        () =>
          window.isSecureContext &&
          !!navigator.mediaDevices?.getUserMedia &&
          !!window.AudioWorkletNode,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("region", { name: "Yerel HTTPS kurulumu", exact: true }),
    ).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});
