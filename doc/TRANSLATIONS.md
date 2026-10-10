# Settings translations

The frontend owns its language independently of the dictation language. Choose
Automatic (Steam) or an explicit interface language under Advanced settings → Interface. Automatic first asks
SteamClient.Settings.GetCurrentLanguage(), with a bounded timeout. Steam names are mapped to available catalogs. navigator.language is a fallback, never the
selected Whisper language. Ten catalogs cover English, Spanish, Russian, Portuguese, Polish, Korean,
Japanese, German, French and Simplified Chinese. Steam's language names and
regional browser locales resolve to these catalogs. Unsupported languages fall
back to English. The override is stored locally in the renderer and does not
alter backend settings, profiles, language codes or recordings.

Catalogs are src/locales/{language}.json, keyed by the English source text.
Add UI strings through t(), not by embedding translated text in components.
Preserve placeholders such as {number}; never translate RPC names, model IDs,
button IDs or game names. Add a catalog and a selector option to support another
language. Missing entries safely fall back to English. Dictation languages use fixed native names in language-names.json, independent
of the interface language. Keep these separate from UI catalogs.

Settings, help, frontend status/fallback messages and frontend notifications are
covered. The native overlay receives the translated transcribing label from the
frontend on initialization and when the interface language changes; Pango renders
Unicode text with font fallback and truncates long labels within the pill. Raw
backend error details, controller diagnostic payloads and custom user preset
names remain untranslated.

Physical test: switch to Español, navigate all pages with the D-pad, confirm
labels fit and Back works, select a transcription language and model, inspect
button/trash focus, run Test Dictation (no send), reopen QAM and confirm locale
persists. Changing interface language must not change transcription language.
Repeat with English, Automatic and the other supported interface languages.
Translations have not yet been reviewed by native speakers; check fit, tone and
terminology, particularly for Russian, Korean, Japanese and Chinese. This test build requires physical validation.
