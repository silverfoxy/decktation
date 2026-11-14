# Recognition context files

In the profile editor, set **Context file** to a local UTF-8 JSON file. Leave it empty to disable external context. Absolute paths and `~` are supported; relative paths resolve from the installed plugin directory. Use **Check context file** to inspect the current snapshot without saving. Save changes to apply it.

```json
{
  "version": 1,
  "source": "my-companion",
  "updated_at": "2026-11-14T18:30:00Z",
  "expires_at": "2026-11-14T18:35:00Z",
  "terms": ["Xal’atath", "Silverfoxy", "Nerub-ar Palace"]
}
```

`version` and `terms` are required. Other fields are optional. `expires_at`, when provided, must be an ISO 8601 timestamp with a timezone. Expired snapshots are ignored. `updated_at` and `source` are descriptive metadata, not freshness checks. Persistent learned vocabulary can omit expiry; transient context should expire.

A companion owns application detection, parsing, ranking, and learned statistics. Export terms in priority order. Decktation never executes the file, interprets application-specific instructions, or uses it to choose a chat channel. An in-game addon whose file writes are restricted needs a companion or converter; WoW SavedVariables are snapshots rather than live updates.

Decktation reads a fresh snapshot for each transcription. Producers should write a temporary file in the same directory and atomically rename it over the destination. Missing, unreadable, malformed, oversized, or expired files contribute no terms; the previous snapshot is discarded. No watcher or network connection is required.

Limits: 64 KiB per file, 100 terms, 100 characters per term, and no control characters. Empty terms are ignored. Manual keywords take priority, followed by external terms, with case-insensitive deduplication. The combined vocabulary is limited to 100 terms and 800 characters including separators; terms that do not fit are skipped. This is a conservative character budget, not an exact tokenizer limit.

Whisper receives the vocabulary through its existing prompt mechanism. The current Parakeet integration does not support phrase boosting; its status is `unsupported`. Hints improve recognition probabilistically and never force transcript substitutions. Vocabulary can bias automatic language detection, so use relevant terms in the spoken language.

Status values are `disabled`, `loaded` (with a term count), `missing`, `invalid`, `expired`, or `unsupported`. Status checks do not return term contents. Context contents are not logged or added to diagnostics.

Legacy WoW snapshots containing `zone`, `boss`, and `target` remain readable. The WoW conversion script now exports this generic format, including saved party names. No installation detection or chat-log learning is included in Decktation.
