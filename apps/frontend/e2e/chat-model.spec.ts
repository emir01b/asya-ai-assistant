import { test, expect, type Page, type WebSocketRoute } from "@playwright/test";

if (process.env.VOICE_TEST_BROWSER_PATH) {
  test.use({
    launchOptions: { executablePath: process.env.VOICE_TEST_BROWSER_PATH },
  });
}

type Frame = {
  type: string;
  model?: string | null;
  request_id?: string;
  text?: string;
};

async function fixture(
  page: Page,
  delayedSettings = false,
  defaultModel = "model-a",
) {
  const frames: Frame[] = [];
  const writes: string[] = [];
  let socket: WebSocketRoute;
  let connections = 0;
  let models = {
    connected: true,
    models: [{ id: "model-a" }, { id: "model-b" }],
    error: null as string | null,
  };
  let modelStatus = 200;
  let modelRequests = 0;
  let releaseSettings!: () => void;
  const settingsGate = new Promise<void>((resolve) => {
    releaseSettings = resolve;
  });
  if (!delayedSettings) releaseSettings();
  await page.route("**/api/v1/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname.replace(
      "/api/v1",
      "",
    );
    if (route.request().method() !== "GET") writes.push(pathname);
    let json: unknown = [];
    if (pathname === "/settings") {
      await settingsGate;
      json = {
        llm_model: defaultModel,
        default_voice: "",
        language: "tr",
        tts_device: "cuda",
        vad_threshold: 0.018,
        vad_silence_ms: 1000,
      };
    } else if (pathname === "/system/status") {
      json = {
        lm: models,
        tts: {},
        stt: {},
        counts: {},
        network: { lan_enabled: false },
      };
    } else if (pathname === "/system/gpu") json = { available: false };
    else if (pathname === "/llm/models") {
      modelRequests++;
      await route.fulfill({
        status: modelStatus,
        json:
          modelStatus === 200
            ? models
            : { detail: "Test model service unavailable" },
      });
      return;
    } else if (pathname === "/conversations")
      json = [{ id: "old", title: "Önceki konuşma", messages: [] }];
    else if (pathname === "/conversations/old")
      json = { id: "old", messages: [] };
    else if (pathname === "/audio/recordings")
      json = { id: "recording-fixture" };
    await route.fulfill({ json });
  });
  await page.routeWebSocket("**/api/v1/realtime/voice", (ws) => {
    connections++;
    socket = ws;
    ws.onMessage((data) => frames.push(JSON.parse(String(data))));
  });
  await page.goto("/");
  await openChat(page);
  return {
    frames,
    writes,
    releaseSettings,
    get connections() {
      return connections;
    },
    get modelRequests() {
      return modelRequests;
    },
    models(value: typeof models, status = 200) {
      models = value;
      modelStatus = status;
    },
    finish() {
      const request = frames
        .filter((f) => f.type === "message" || f.type === "audio")
        .at(-1)!;
      socket.send(
        JSON.stringify({
          type: "done",
          request_id: request.request_id,
          message: { id: "reply", role: "assistant", content: "Tamam" },
        }),
      );
    },
  };
}

async function openChat(page: Page) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Sesli sohbet", exact: true })
    .click();
  await expect(page.getByText("Sohbet bağlı", { exact: true })).toBeVisible();
}

async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "Sohbet mesajı" }).fill(text);
  await page.getByRole("button", { name: "Mesaj gönder" }).click();
}

test("late settings initialize the model; selection survives conversation switches and resets on remount", async ({
  page,
}) => {
  const f = await fixture(page, true);
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  f.releaseSettings();
  await expect(select).toHaveValue("model-a");
  await select.selectOption("model-b");
  await page
    .getByRole("button", { name: "Önceki konuşma", exact: true })
    .click();
  await expect(select).toHaveValue("model-b");
  await page.getByRole("button", { name: "Yeni konuşma", exact: true }).click();
  await expect(select).toHaveValue("model-b");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Ses Stüdyosu", exact: true })
    .click();
  await openChat(page);
  await expect(select).toHaveValue("model-a");
  expect(f.writes).not.toContain("/settings");
});

test("changing a model during a response affects only the next request and keeps the socket", async ({
  page,
}) => {
  const f = await fixture(page);
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  await expect(select).toHaveValue("model-a");
  const initialConnections = f.connections;
  await send(page, "İlk mesaj");
  await expect
    .poll(() => f.frames.filter((v) => v.type === "message"))
    .toHaveLength(1);
  const first = { ...f.frames.find((v) => v.type === "message")! };
  await select.selectOption("model-b");
  expect(f.frames).toEqual([first]);
  expect(first.model).toBe("model-a");
  f.finish();
  await send(page, "İkinci mesaj");
  await expect
    .poll(() =>
      f.frames.filter((v) => v.type === "message").map((v) => v.model),
    )
    .toEqual(["model-a", "model-b"]);
  expect(f.connections).toBe(initialConnections);
  expect(f.writes).not.toContain("/settings");
});

test("late settings do not overwrite a choice already made by the user", async ({
  page,
}) => {
  const f = await fixture(page, true);
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  await expect(
    select.getByRole("option", { name: "model-b", exact: true }),
  ).toHaveCount(1);
  await select.selectOption("model-b");
  const settingsResponse = page.waitForResponse("**/api/v1/settings");
  f.releaseSettings();
  await (await settingsResponse).finished();
  // Allow the settings fetch continuation, React render, and its passive effect
  // to finish before checking that the user's existing choice survived.
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
  await page
    .getByRole("button", { name: "Durumu yenile", exact: true })
    .click();
  await expect(select).toHaveValue("model-b");
  await send(page, "Seçimim korunsun");
  await expect
    .poll(() => f.frames.find((v) => v.type === "message")?.model)
    .toBe("model-b");
  expect(f.writes).not.toContain("/settings");
});

test("refresh retains unavailable choice, shows failures, and recovers with new models", async ({
  page,
}) => {
  const f = await fixture(page, false, "custom-model");
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  const refresh = page.getByRole("button", { name: "Modelleri yenile" });
  await expect(select).toHaveValue("custom-model");
  const initialRequests = f.modelRequests;
  f.models({ connected: true, models: [], error: null });
  await refresh.click();
  await expect.poll(() => f.modelRequests).toBe(initialRequests + 1);
  await expect(
    page.getByRole("status").filter({ hasText: /model listesi boş/ }),
  ).toBeVisible();
  await expect(select).toHaveValue("custom-model");
  f.models(
    { connected: false, models: [], error: "Test model service unavailable" },
    503,
  );
  await refresh.click();
  await expect(
    page.getByText(/Test model service unavailable/).first(),
  ).toBeVisible();
  await expect(select).toHaveValue("custom-model");
  f.models({ connected: false, models: [], error: "LM Studio is offline" });
  await refresh.click();
  await expect(
    page.getByRole("status").filter({ hasText: "LM Studio is offline" }),
  ).toBeVisible();
  await expect(select).toHaveValue("custom-model");
  f.models({ connected: true, models: [{ id: "model-c" }], error: null });
  await refresh.click();
  await expect(
    select.getByRole("option", { name: "model-c", exact: true }),
  ).toHaveCount(1);
  await expect(select).toHaveValue("custom-model");
  await select.selectOption("model-c");
  await send(page, "Yeni model");
  await expect
    .poll(() => f.frames.find((v) => v.type === "message")?.model)
    .toBe("model-c");
});

test("empty model lists still allow a default-server request", async ({
  page,
}) => {
  const f = await fixture(page, false, "");
  f.models({ connected: true, models: [], error: null });
  await page.getByRole("button", { name: "Modelleri yenile" }).click();
  await expect(
    page.getByRole("combobox", { name: "Sohbet modeli" }),
  ).toHaveValue("");
  await send(page, "Merhaba");
  await expect
    .poll(() => f.frames.find((v) => v.type === "message")?.model)
    .toBeNull();
});

test("an already-running microphone uses the latest model without restarting capture", async ({
  page,
}) => {
  // Mock browser hardware boundaries, retaining the production Microphone and VAD.
  await page.addInitScript(() => {
    const state = {
      starts: 0,
      stops: 0,
      node: null as null | {
        port: { onmessage: null | ((event: { data: Float32Array }) => void) };
      },
    };
    Object.assign(window, { captureFixture: state });
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: async () => {
          state.starts++;
          return { getTracks: () => [{ stop: () => state.stops++ }] };
        },
      },
    });
    class Node {
      port = {
        onmessage: null as null | ((event: { data: Float32Array }) => void),
      };
      constructor() {
        state.node = this;
      }
      connect() {}
      disconnect() {}
    }
    class Context {
      sampleRate = 16000;
      state = "running";
      destination = {};
      audioWorklet = { addModule: async () => {} };
      createMediaStreamSource() {
        return { connect() {} };
      }
      createGain() {
        return { gain: { value: 0 }, connect() {} };
      }
      async resume() {}
      async close() {
        this.state = "closed";
      }
    }
    Object.assign(window, { AudioContext: Context, AudioWorkletNode: Node });
  });
  const f = await fixture(page);
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  await expect(select).toHaveValue("model-a");
  const initialConnections = f.connections;
  await page.getByRole("button", { name: "Mikrofonu aç", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Mikrofonu kapat", exact: true }),
  ).toBeVisible();
  await select.selectOption("model-b");
  await page.evaluate(() => {
    const fixture = (
      window as unknown as {
        captureFixture: {
          node: { port: { onmessage: (e: { data: Float32Array }) => void } };
        };
      }
    ).captureFixture;
    for (let i = 0; i < 5; i++)
      fixture.node.port.onmessage({ data: new Float32Array(1600).fill(0.1) });
    for (let i = 0; i < 12; i++)
      fixture.node.port.onmessage({ data: new Float32Array(1600) });
  });
  await expect
    .poll(() => f.frames.find((v) => v.type === "audio")?.model)
    .toBe("model-b");
  expect(
    await page.evaluate(() => {
      const f = (
        window as unknown as {
          captureFixture: { starts: number; stops: number };
        }
      ).captureFixture;
      return { starts: f.starts, stops: f.stops };
    }),
  ).toEqual({ starts: 1, stops: 0 });
  expect(f.connections).toBe(initialConnections);
});

test("a newer refresh wins over an older delayed model response", async ({
  page,
}) => {
  await fixture(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = false;
  let calls = 0;
  await page.route("**/api/v1/llm/models", async (route) => {
    const first = ++calls === 1;
    if (first) {
      held = true;
      await gate;
    }
    try {
      await route.fulfill({
        json: {
          connected: true,
          models: [{ id: first ? "stale-model" : "fresh-model" }],
          error: null,
        },
      });
    } catch {
      /* Superseded requests are intentionally aborted. */
    }
  });
  const refresh = page.getByRole("button", { name: "Modelleri yenile" });
  await refresh.click();
  await expect.poll(() => held).toBe(true);
  await expect(
    page.getByRole("status").filter({ hasText: "Modeller yükleniyor" }),
  ).toBeVisible();
  await refresh.click();
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  await expect(
    select.getByRole("option", { name: "fresh-model", exact: true }),
  ).toHaveCount(1);
  release();
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
  await expect(
    select.getByRole("option", { name: "stale-model", exact: true }),
  ).toHaveCount(0);
  await expect(select).toHaveValue("model-a");
});

test("model controls remain within a narrow screen", async ({ page }) => {
  await fixture(
    page,
    false,
    "a-very-long-custom-model-identifier-that-is-not-present-in-the-server-model-list",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  const select = page.getByRole("combobox", { name: "Sohbet modeli" });
  await expect(select).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Modelleri yenile" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
