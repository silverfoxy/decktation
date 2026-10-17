# Privacy and permissions

## Local processing

Audio recording, transcription, chat parsing, and text entry run on the Steam Deck. Decktation does not upload audio, transcripts, or WoW context. The first use of a selected Whisper model downloads model files from Hugging Face; after download, transcription runs locally while the model is cached on the device.

## Optional diagnostics

**Diagnostics → Share** is off by default. When enabled, Decktation sends scrubbed errors, performance samples, and exact application counters to Sentry. Counters record the inference backend used for each request (Vulkan or CPU), failed inference attempts, and explicit draft cancellations by source. Performance samples include audio length, audio preparation time, inference time, and total transcription time. Metrics also include the selected model size and coarse runtime categories: Steam Deck or other device, OS family and major/minor version, and processor architecture.

Ongoing diagnostics exclude audio, transcript and chat text, WoW context, credentials, hostnames, serial numbers, Bluetooth addresses, raw hardware model strings, individual button-press streams, IP addresses, full kernel versions, and paths containing the local username. You can turn sharing off at any time in **Diagnostics → Share**. Sentry is not initialized for ongoing sharing while it is off; the separate debugger upload below initializes an isolated client only when requested.

**Controller input debugger** is separate from the Share toggle. Only after you press **Start 30-second capture** does it locally collect controller interfaces (including rejected evdev interfaces), numeric bus/vendor/product IDs, advertised key/axis codes, press/release transitions including unmapped keys, decoded HID button transitions, source changes, and binding observations. After Stop or the 30-second limit, the listener continues reading controller events for up to 250 ms before finalizing; report timestamps are capped at 30 seconds. The report also includes the Decktation version; OS ID, version, and build; full kernel release; architecture; DMI device manufacturer/model/product version/SKU and board name/version; CPU model; and BIOS version/date when available. Device serials, device names from input interfaces, addresses, input paths, keyboard typing, audio, and transcripts are excluded. If an input interface exposes both keyboard and controller capabilities, only allowlisted controller-button and D-pad codes are recorded; ordinary keyboard key codes are discarded. The local report is limited to 16 interfaces, 256 events, and 32 KiB. The local preview shows event/interface counts and how many host-metadata fields were available; unavailable values are omitted. The sanitized report is displayed for review; pressing **Send this report to Sentry** is a separate, explicit per-report consent. This uploads one Sentry event with a JSON attachment and an event ID, regardless of the continuous Share setting. Merely recording or viewing the report sends nothing. A queued event ID does not prove remote delivery.

## Controller capture controls

The backend owns one session with explicit starting, recording, stopping, ready, and failed states. The 30-second recording window starts when the controller listener acknowledges that session, not when the user clicks Start or from the browser clock. The countdown is reported by the backend. A missing or dead listener produces an error instead of an apparently completed empty report. Reopening the panel reconnects to the existing session; closing the panel does not stop or upload it.

During capture, a dedicated focusable screen consumes Decky controller navigation events (including A/confirm, B/back, and directional navigation). Controller presses therefore exercise the diagnostic recorder rather than buttons in the plugin UI. Steam and Quick Access remain system-reserved and may open system menus. Capture ends automatically after 30 seconds; a touch/mouse-only **Stop and review** control permits an early stop. Normal push-to-talk actions are suppressed until capture ends and held buttons have been released. This is UI event handling, not an exclusive operating-system input-device grab. Ordinary keyboard typing remains excluded from the report.

## Decky permission

Decktation declares Decky’s `_root` permission for controller input and text entry:

- It reads Valve raw controller reports from `/dev/hidraw*` so Steam Deck buttons and grips work independently of a game’s Steam Input layout.
- It reads gamepad events from `/dev/input/event*` for other controllers. It does not exclusively grab devices or change their mappings.
- Its bundled `ydotoold` helper uses `/dev/uinput` to enter the transcription in the active window. The helper uses a private, owner-only socket in `/tmp` and stops when the plugin unloads.
- Transcribed text is passed to the helper as data; it is never evaluated as a shell command.

Decktation does not install system packages, modify the system filesystem, or create system services.
