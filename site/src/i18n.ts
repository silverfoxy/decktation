import en from './i18n/en.json';
import es from './i18n/es.json';

export const dictionaries = { en, es };
export const locales = ['en', 'es'] as const;
export type Locale = typeof locales[number];
export const localeNames = { en: 'English', es: 'Español' };

for (const locale of locales) {
  const keys = Object.keys(dictionaries[locale]).sort();
  if (JSON.stringify(keys) !== JSON.stringify(Object.keys(en).sort())) {
    throw new Error(`Incomplete translation: ${locale}`);
  }
}
