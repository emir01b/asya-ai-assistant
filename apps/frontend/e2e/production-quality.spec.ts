import { test, expect, type Page } from "@playwright/test";

if (process.env.VOICE_TEST_BROWSER_PATH) {
  test.use({
    launchOptions: { executablePath: process.env.VOICE_TEST_BROWSER_PATH },
  });
}

function wav(seconds: number) {
  const samples = Math.round(seconds * 8000);
  const data = Buffer.alloc(44 + samples * 2);
  data.write("RIFF", 0);
  data.writeUInt32LE(data.length - 8, 4);
  data.write("WAVEfmt ", 8);
  data.writeUInt32LE(16, 16);
  data.writeUInt16LE(1, 20);
  data.writeUInt16LE(1, 22);
  data.writeUInt32LE(8000, 24);
  data.writeUInt32LE(16000, 28);
  data.writeUInt16LE(2, 32);
  data.writeUInt16LE(16, 34);
  data.write("data", 36);
  data.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++)
    data.writeInt16LE(Math.round(1000 * Math.sin(i * 0.15)), 44 + i * 2);
  return data;
}

async function fixture(
  page: Page,
  overrides: Record<string, unknown> = {},
  jobOverrides: Record<string, unknown> = {},
) {
  let settings = {
    lm_url: "http://127.0.0.1:1234/v1",
    llm_model: "",
    temperature: 0.7,
    system_prompt: "Yerel asistan",
    chat_speech_rate: 0.9,
    offline: true,
    tts_device: "cuda",
    stt_device: "cuda",
    stt_model: "large-v3-turbo",
    stt_cpu_fallback: true,
    language: "tr",
    default_voice: "voice-a",
    vad_threshold: 0.018,
    vad_silence_ms: 1000,
    microphone_id: "",
    output_id: "",
    debug: false,
    // Deliberately omit new fields to exercise old settings compatibility.
    ...overrides,
  } as Record<string, unknown>;
  let voices = [
    {
      id: "voice-a",
      name: "Anlatıcı",
      language: "en",
      asset_id: "full-a",
      original_asset_id: "original-a",
      reference_asset_id: "ref-a",
      reference_start: 1,
      reference_end: 9,
      warnings: ["Kayıtta uzun sessizlikler var."],
      duration: 16,
      sample_rate: 8000,
      consent: true,
      exaggeration: 0.7,
      cfg_weight: 0.3,
      created_at: "2026-10-31T10:00:00Z",
    },
  ];
  let job = {
    id: "job-a",
    created_at: "2026-10-31T10:00:00Z",
    text: "Merhaba dünya.",
    voice_id: "voice-a",
    language: "tr",
    provider: "chatterbox",
    exaggeration: 0,
    cfg_weight: 0,
    speech_rate: 1,
    trailing_pause_ms: 0,
    speech_quality: "quality",
    compare_candidates: true,
    seed: 0,
    reference_asset_id: "ref-a",
    status: "completed",
    progress: 1,
    segments: [],
    error: null,
    metrics: { duration: 8, total_seconds: 2, rtf: 0.25 },
    asset_id: "candidate-a",
    selected_candidate: 0,
    candidates: [
      { index: 0, seed: 0, asset_id: "candidate-a" },
      { index: 1, seed: 1, asset_id: "candidate-b" },
    ],
    ...jobOverrides,
  };
  const writes: { path: string; body: Record<string, unknown> | null }[] = [];
  let voiceReads = 0;
  const audio = wav(16);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    const mutation = request.method() !== "GET";
    const body =
      mutation && !request.headers()["content-type"]?.includes("multipart")
        ? request.postDataJSON()
        : null;
    if (mutation) writes.push({ path, body });
    let json: unknown;
    if (path === "/settings") {
      if (mutation) settings = body;
      json = settings;
    } else if (path === "/voices") {
      if (mutation)
        voices = [
          ...voices,
          { ...voices[0], id: "voice-new", name: "Yeni ses" },
        ];
      else voiceReads++;
      json = mutation ? voices[voices.length - 1] : voices;
    } else if (path.startsWith("/voices/")) {
      voices = voices.map((voice) =>
        path.endsWith(voice.id) ? { ...voice, ...body } : voice,
      );
      json = voices.find((voice) => path.endsWith(voice.id));
    } else if (path === "/tts/generate") json = { ...job, ...body };
    else if (path === "/tts/history/job-a/select-candidate") {
      const index = body.index as number;
      job = {
        ...job,
        selected_candidate: index,
        asset_id: job.candidates[index].asset_id,
      };
      json = job;
    } else if (path === "/tts/history") json = [job];
    else if (path === "/system/status")
      json = {
        lm: { connected: false, models: [], error: null },
        tts: {},
        stt: {},
        counts: {},
        network: { lan_enabled: false },
      };
    else if (path === "/system/gpu") json = { available: false };
    else if (path.endsWith("/peaks")) json = { peaks: [0.2, 0.6, 0.9, 0.3] };
    else if (path.startsWith("/audio/")) {
      await route.fulfill({ contentType: "audio/wav", body: audio });
      return;
    } else if (path === "/agent-admin")
      json = {
        enabled: false,
        agents: [],
        scopes: [],
        url: "http://localhost:8001",
        guide: "/guide",
      };
    else if (path === "/agent-admin/installation")
      json = {
        installed: false,
        status: "not_installed",
        progress: 0,
        message: "Kurulu değil",
        error: null,
        running: false,
      };
    else {
      await route.fulfill({
        status: 404,
        json: { detail: `Unmocked endpoint ${path}` },
      });
      return;
    }
    await route.fulfill({ json });
  });
  await page.goto("/");
  await expect(page.getByLabel("Ses profili", { exact: true })).toHaveValue(
    "voice-a",
  );
  return {
    writes,
    get voiceReads() {
      return voiceReads;
    },
  };
}

async function navigate(page: Page, name: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}

test("quality and comparison defaults survive saving and reload while tempo stays separate", async ({
  page,
}) => {
  const state = await fixture(page);
  await navigate(page, "Ayarlar");
  const quality = page.getByLabel("ÜRETİM KALİTESİ", { exact: true });
  const comparison = page.getByLabel("İki aday üret ve karşılaştır", {
    exact: true,
  });
  await expect(quality).toHaveValue("balanced");
  await expect(comparison).not.toBeChecked();
  await quality.selectOption("quality");
  await comparison.check();
  await page
    .getByRole("button", { name: "Ayarları kaydet", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Ayarlar kaydedildi" }),
  ).toBeVisible();
  expect(
    state.writes.find((write) => write.path === "/settings")?.body,
  ).toMatchObject({
    speech_quality: "quality",
    compare_candidates: true,
    chat_speech_rate: 0.9,
  });
  await page.reload();
  await navigate(page, "Ayarlar");
  await expect(quality).toHaveValue("quality");
  await expect(comparison).toBeChecked();
  await expect(
    page.getByRole("slider", { name: "Sohbet konuşma hızı", exact: true }),
  ).toHaveValue("0.9");
  await page.screenshot({
    path: "../../docs/quality-settings-mocked.png",
    fullPage: true,
  });
});

test("saved profile initializes studio, zero settings persist, and both candidates can be selected", async ({
  page,
}) => {
  const state = await fixture(page, {
    speech_quality: "quality",
    compare_candidates: true,
  });
  const expression = page.getByRole("slider", {
    name: "İfade yoğunluğu",
    exact: true,
  });
  const cfg = page.getByRole("slider", { name: "CFG ağırlığı", exact: true });
  await expect(expression).toHaveValue("0.7");
  await expect(cfg).toHaveValue("0.3");
  await expression.focus();
  await expression.press("Home");
  await cfg.focus();
  await cfg.press("Home");
  const beforeRefresh = state.voiceReads;
  await page
    .getByRole("button", { name: "Durumu yenile", exact: true })
    .click();
  await expect.poll(() => state.voiceReads).toBeGreaterThan(beforeRefresh);
  await expect(expression).toHaveValue("0");
  await expect(cfg).toHaveValue("0");
  const reads = state.voiceReads;
  await page
    .getByRole("button", {
      name: "İfade ve CFG’yi seçili profile kaydet",
      exact: true,
    })
    .click();
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "İfade ve CFG ses profiline kaydedildi" }),
  ).toBeVisible();
  expect(
    state.writes.find((write) => write.path === "/voices/voice-a")?.body,
  ).toEqual({
    name: "Anlatıcı",
    language: "en",
    exaggeration: 0,
    cfg_weight: 0,
  });
  expect(state.voiceReads).toBeGreaterThan(reads);
  await page.getByLabel("Seslendirilecek metin").fill("Merhaba dünya.");
  await page.getByLabel("SEED (İSTEĞE BAĞLI)", { exact: true }).fill("0");
  await page.getByRole("button", { name: "Ses oluştur", exact: true }).click();
  await expect(
    page.getByLabel("Üretim adayları", { exact: true }),
  ).toBeVisible();
  expect(
    state.writes.find((write) => write.path === "/tts/generate")?.body,
  ).toMatchObject({ exaggeration: 0, cfg_weight: 0, seed: 0 });
  await expect(
    page.getByRole("button", { name: "Aday A seçili", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Aday B seç", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Aday B seçili", exact: true }),
  ).toBeDisabled();
  expect(state.writes.at(-1)).toEqual({
    path: "/tts/history/job-a/select-candidate",
    body: { index: 1 },
  });
  await expect(
    page
      .getByText("Üretilen ses", { exact: true })
      .locator("..")
      .locator("..")
      .locator("audio"),
  ).toHaveAttribute("src", /candidate-b/);
  await page.screenshot({
    path: "../../docs/quality-studio-mocked.png",
    fullPage: true,
  });
  await navigate(page, "Üretim geçmişi");
  await expect(
    page.getByRole("button", { name: "Aday B seçili", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Aday A seç", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Aday A seçili", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Yeniden üret", exact: true }).click();
  await expect(expression).toHaveValue("0");
  await expect(cfg).toHaveValue("0");
  await expect(
    page.getByLabel("SEED (İSTEĞE BAĞLI)", { exact: true }),
  ).toHaveValue("0");
});

test("library validates length before upload and previews and saves an explicit reference trim", async ({
  page,
}) => {
  const state = await fixture(page);
  await navigate(page, "Ses kütüphanesi");
  await expect(
    page.getByText("En fazla 5 dakika · 200 MB · Önerilen klip 6–10 sn", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Kayıtta uzun sessizlikler var.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Orijinal dosyayı indir", exact: true }),
  ).toHaveAttribute("href", /original-a/);
  await expect(
    page.getByRole("link", { name: "Tam kaydı dinle", exact: true }),
  ).toHaveAttribute("href", /full-a/);
  await expect(
    page.getByLabel("Anlatıcı referansı", { exact: true }),
  ).toHaveAttribute("src", /ref-a/);
  await page
    .getByRole("button", { name: "Referans klibini düzenle", exact: true })
    .click();
  await page.getByLabel("Klip başlangıcı", { exact: true }).fill("2");
  await page.getByLabel("Klip bitişi", { exact: true }).fill("10");
  await page
    .getByRole("button", { name: "Seçili klibi dinle", exact: true })
    .click();
  const preview = page.getByLabel("Klip önizlemesi", { exact: true });
  await expect
    .poll(() =>
      preview.evaluate((audio) => (audio as HTMLAudioElement).currentTime),
    )
    .toBeGreaterThanOrEqual(2);
  expect(state.writes).toEqual([]);
  await page
    .getByRole("button", { name: "Referans klibini kaydet", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Referans klibi kaydedildi" }),
  ).toBeVisible();
  expect(state.writes[0].body).toMatchObject({
    reference_start: 2,
    reference_end: 10,
    name: "Anlatıcı",
    language: "en",
    exaggeration: 0.7,
    cfg_weight: 0.3,
  });
  await page
    .getByLabel("Referans ses dosyası", { exact: true })
    .setInputFiles({
      name: "too-long.wav",
      mimeType: "audio/wav",
      buffer: wav(301),
    });
  await expect(page.getByRole("alert")).toContainText("5 dakika");
  await expect(
    page.getByRole("button", { name: "Profili oluştur", exact: true }),
  ).toBeDisabled();
  expect(state.writes.filter((write) => write.path === "/voices")).toEqual([]);
  await page
    .getByLabel("Referans ses dosyası", { exact: true })
    .setInputFiles({
      name: "voice.wav",
      mimeType: "audio/wav",
      buffer: wav(16),
    });
  await page.getByLabel("PROFİL ADI", { exact: true }).fill("Yeni ses");
  await page
    .getByLabel("Bu sesin hak sahibiyim veya kullanım iznim var.")
    .check();
  await page
    .getByRole("button", { name: "Profili oluştur", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Yeni ses", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Yeni ses referans klibi", { exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../docs/quality-reference-mobile-mocked.png",
    fullPage: true,
  });
});

test("history exposes candidate generation and scoring failures without hiding the usable audio", async ({
  page,
}) => {
  await fixture(
    page,
    {},
    {
      candidates: [
        {
          index: 0,
          seed: 0,
          asset_id: "candidate-a",
          scoring: { error: "Değerlendirme modeli yüklenemedi" },
        },
      ],
      candidate_errors: [{ seed: 1, error: "İkinci aday üretilemedi" }],
    },
  );
  await navigate(page, "Üretim geçmişi");
  await expect(
    page.getByLabel("Aday üretim uyarıları", { exact: true }),
  ).toContainText("Seed 1: İkinci aday üretilemedi");
  await expect(
    page.getByText(
      "Değerlendirme yapılamadı: Değerlendirme modeli yüklenemedi",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Karşılaştırma için yalnızca 1 aday hazır. İkinci aday üretilememiş olabilir.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Aday A seçili", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".history-card > audio")).toHaveAttribute(
    "src",
    /candidate-a/,
  );
});
