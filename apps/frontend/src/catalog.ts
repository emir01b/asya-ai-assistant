import {
  Activity,
  AudioLines,
  FolderClock,
  Headphones,
  LayoutDashboard,
  MessageCircle,
  Settings2,
} from "lucide-react";
export const pages = [
  ["dashboard", "Genel bakış", LayoutDashboard],
  ["studio", "Ses Stüdyosu", AudioLines],
  ["chat", "Sesli sohbet", MessageCircle],
  ["library", "Ses kütüphanesi", Headphones],
  ["history", "Üretim geçmişi", FolderClock],
  ["diagnostics", "Tanılama", Activity],
  ["settings", "Ayarlar", Settings2],
] as const;
export type Page = (typeof pages)[number][0];
export const languageNames: Record<string, string> = {
  tr: "Türkçe",
  en: "English",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
  it: "Italiano",
  pt: "Português",
  ru: "Русский",
  ar: "العربية",
  ja: "日本語",
  ko: "한국어",
  zh: "中文",
  da: "Dansk",
  el: "Ελληνικά",
  fi: "Suomi",
  he: "עברית",
  hi: "हिन्दी",
  ms: "Melayu",
  nl: "Nederlands",
  no: "Norsk",
  pl: "Polski",
  sv: "Svenska",
  sw: "Kiswahili",
};
export const presets = [
  ["Normal", 0.5, 0.5],
  ["Sakin", 0.3, 0.6],
  ["Heyecanlı", 0.8, 0.45],
  ["Dramatik", 1, 0.4],
  ["Yumuşak", 0.25, 0.65],
  ["Enerjik", 0.9, 0.5],
] as const;
export const titleMap: Record<Page, [string, string]> = {
  dashboard: [
    "Her şey, tek bir stüdyoda.",
    "Yerel ses üretiminiz ve modelleriniz bir arada.",
  ],
  studio: [
    "Sözcüklerinize ses verin.",
    "Metninizi yazın. Sesinizi seçin. Hikâyenizi duyurun.",
  ],
  chat: [
    "Konuşmak kadar doğal.",
    "Yerel modellerinizle sesli bir sohbet başlatın.",
  ],
  library: [
    "Her sesin bir karakteri var.",
    "Kendi ses profillerinizi güvenle oluşturun ve yönetin.",
  ],
  history: [
    "Ürettiğiniz her ses burada.",
    "Geçmiş kayıtları dinleyin, karşılaştırın ve yeniden üretin.",
  ],
  diagnostics: [
    "Tahmin değil, ölçüm.",
    "Gerçek görevlerden gelen performans ve hata kayıtları.",
  ],
  settings: [
    "Stüdyonuz, sizin ayarlarınız.",
    "Yerel modelleri, ses cihazlarını ve varsayılanları yönetin.",
  ],
};
