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

`version` identifies the **context file format**, not the game, addon, model, or a sequence number. Always write the integer `1` for the current format, even when updating terms, timestamps, or the producer itself. A future incompatible format would use a new version; adding optional fields does not necessarily require one. Decktation currently accepts only version `1` for this format and ignores snapshots with an unsupported version. The legacy WoW format is handled separately for compatibility.

A companion owns application detection, parsing, ranking, and learned statistics. Export terms in priority order. Decktation never executes the file, interprets application-specific instructions, or uses it to choose a chat channel. An in-game addon whose file writes are restricted needs a companion or converter; WoW SavedVariables are snapshots rather than live updates.

Decktation reads a fresh snapshot for each transcription. Producers should write a temporary file in the same directory and atomically rename it over the destination. Missing, unreadable, malformed, oversized, or expired files contribute no terms; the previous snapshot is discarded. No watcher or network connection is required.

Limits: 64 KiB per file, 100 terms, 100 characters per term, and no control characters. Empty terms are ignored. Manual keywords take priority, followed by external terms, with case-insensitive deduplication. The combined vocabulary is limited to 100 terms and 800 characters including separators; terms that do not fit are skipped. This is a conservative character budget, not an exact tokenizer limit.

Whisper receives the vocabulary through its existing prompt mechanism. The current Parakeet integration does not support phrase boosting; its status is `unsupported`. Hints improve recognition probabilistically and never force transcript substitutions. Vocabulary can bias automatic language detection, so use relevant terms in the spoken language.

## Parakeet support depends on the runtime

Parakeet is not inherently unable to use recognition vocabulary. As checked on 2026-11-14:

- NVIDIA [NeMo word boosting](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/asr_customization/word_boosting.html) supports decoding-time phrase boosting for CTC and RNN-T/TDT models, explicitly including Parakeet-TDT v2. This biases vocabulary without retraining; it is different from accepting a Whisper-style prose prompt.
- NVIDIA [Speech NIM customization](https://docs.nvidia.com/nim/speech/26.10.0/asr/customization/customization.html) lists word boosting for Parakeet CTC, multilingual 0.6B TDT, and multilingual 1.1B RNNT deployments. These are different runtimes from the one bundled with Decktation.
- Decktation bundles transcribe.cpp v0.4.1 and runs its Parakeet v3 and Ultra models on CPU. Its adapter currently calls `session.run(pcm)` without vocabulary. Upstream [transcribe.cpp PR #221](https://github.com/handy-computer/transcribe.cpp/pull/221) proposes phrase boosting for offline TDT and RNN-T greedy decoding, including v3 and Ultra, but remains open and unmerged. The proposal excludes streaming and CTC heads.

Consequently, selecting another bundled Parakeet model does not enable context today. Supporting it requires a compatible runtime implementation and adapter integration, followed by recognition-quality and performance validation. The generic context file can supply vocabulary when that support is added; its format version need not change solely because another engine supports it.

Status values are `disabled`, `loaded` (with a term count), `missing`, `invalid`, `expired`, or `unsupported`. Status checks do not return term contents. Context contents are not logged or added to diagnostics.

Legacy WoW snapshots containing `zone`, `boss`, and `target` remain readable. The WoW conversion script now exports this generic format, including saved party names. No installation detection or chat-log learning is included in Decktation.
