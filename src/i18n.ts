import en from "./locales/en.json";
import nativeLanguageNames from "./locales/language-names.json";
import es from "./locales/es.json";
import ru from "./locales/ru.json";
import pt from "./locales/pt.json";
import pl from "./locales/pl.json";
import ko from "./locales/ko.json";
import ja from "./locales/ja.json";
import de from "./locales/de.json";
import fr from "./locales/fr.json";
import zh from "./locales/zh.json";

const catalogs = { en, es, ru, pt, pl, ko, ja, de, fr, zh };
export type InterfaceLocale = keyof typeof catalogs;
export type InterfacePreference = "auto" | InterfaceLocale;
export const INTERFACE_LANGUAGE_OPTIONS = [
    {data:"en",label:"English"}, {data:"es",label:"Español"},
    {data:"ru",label:"Русский"}, {data:"pt",label:"Português"},
    {data:"pl",label:"Polski"}, {data:"ko",label:"한국어"},
    {data:"ja",label:"日本語"}, {data:"de",label:"Deutsch"},
    {data:"fr",label:"Français"}, {data:"zh",label:"中文（简体）"},
];
function isLocale(value: unknown): value is InterfaceLocale {
    return typeof value === "string" && Object.prototype.hasOwnProperty.call(catalogs, value);
}
const STORAGE_KEY = "decktation.interfaceLanguage";
let preference: InterfacePreference = "auto";
let steamLanguage: string | undefined;
try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (isLocale(saved)) preference = saved;
} catch (_) { /* Storage may be unavailable in the Steam renderer. */ }

export function getInterfacePreference(): InterfacePreference { return preference; }
export function setInterfacePreference(value: InterfacePreference): void {
    if (value !== "auto" && !isLocale(value)) return;
    preference = value;
    try { window.localStorage.setItem(STORAGE_KEY, value); } catch (_) {}
}
export function resolveLocale(value: InterfacePreference, systemLanguage: string): InterfaceLocale {
    if (value !== "auto") return value;
    const steamNames: Record<string, InterfaceLocale> = {
        english:"en", spanish:"es", latam:"es", russian:"ru",
        portuguese:"pt", brazilian:"pt", polish:"pl", koreana:"ko", korean:"ko",
        japanese:"ja", german:"de", french:"fr", schinese:"zh", tchinese:"zh",
    };
    const name = systemLanguage.toLowerCase();
    const code = name.split(/[-_]/)[0];
    return steamNames[name] || (isLocale(code) ? code : "en");
}
export async function initializeSteamLanguage(): Promise<void> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
        const settings = (window as any).SteamClient?.Settings;
        if (typeof settings?.GetCurrentLanguage !== "function") return;
        const value = await Promise.race([
            settings.GetCurrentLanguage(),
            new Promise(resolve => { timer = setTimeout(() => resolve(undefined), 1500); }),
        ]);
        if (typeof value === "string" && value) steamLanguage = value;
    } catch (_) { /* Use navigator.language if Steam cannot provide its locale. */ }
    finally { if (timer !== undefined) clearTimeout(timer); }
}
function locale(): InterfaceLocale {
    return resolveLocale(preference, steamLanguage || (typeof navigator === "undefined" ? "en" : navigator.language));
}
export function t(key: string, values: Record<string, string | number> = {}): string {
    const english = en as Record<string, string>;
    const translated = catalogs[locale()] as Record<string, string>;
    const text = translated[key] || english[key] || key;
    return text.replace(/\{(\w+)\}/g, (match, name) => values[name] === undefined ? match : String(values[name]));
}
export function languageName(code: string, fallback: string): string {
    if (code === "auto") return t("Auto Detect");
    // Autonyms are independent of the interface locale and ICU/browser data.
    // Keep Whisper codes untouched; only change the displayed names.
    return (nativeLanguageNames as Record<string, string>)[code] || fallback;
}
