# World of Warcraft context

Decktation can use context from the optional **DecktationContext** WoW addon to improve recognition of names and game terms. The addon and conversion script run locally. The current SavedVariables transport provides snapshots, not reliable live updates.

## Current limitation

The addon updates its context in memory, but WoW does not write SavedVariables to disk on every Lua update. The converter’s `--watch` mode watches the file on disk, so target, group, and zone changes can remain stale until WoW next writes that file, such as on a UI reload or logout. This is tracked in [upstream issue #13](https://github.com/silverfoxy/decktation/issues/13).

The WoW preset still has a built-in vocabulary prompt. The addon may add the most recently saved context, but users should not rely on it to follow changes during a play session. A pixel-based real-time companion is being discussed in [upstream issue #36](https://github.com/silverfoxy/decktation/issues/36); it is a proposal, not an implemented feature, and SteamOS Gamescope capture remains an open question.

## Set up the addon

Copy [`WowAddon/DecktationContext`](../WowAddon/DecktationContext/) into WoW’s `Interface/AddOns/` directory. Start WoW, enable **Decktation Context** in the AddOns list, and log in. The addon tracks the current zone, target or encounter, group members, class, and specialization. Type `/decktation` in game to display the current context.

The addon saves its data to:

```text
WTF/Account/<account>/SavedVariables/DecktationContext.lua
```

On Steam Deck with Proton, the file is under the game’s `compatdata` directory. You can locate it with:

```bash
find ~/.local/share/Steam/steamapps/compatdata -name DecktationContext.lua 2>/dev/null
```

## Convert and connect the context

The converter exports the generic [recognition context format](RECOGNITION_CONTEXT.md). You can select its output using **Context file** in any profile; the built-in WoW profiles retain their default `wow_context.json` path.

From the repository root, run the converter at `backend/src/convert_wow_context.py`:

```bash
python3 backend/src/convert_wow_context.py \
  --input "/path/to/DecktationContext.lua" \
  --output wow_context.json
```

Add `--watch` to regenerate the JSON when the SavedVariables file changes. It cannot make the context live if WoW has not flushed new values to disk. The Decky plugin’s WoW preset reads `wow_context.json` from the installed plugin directory (`$DECKY_PLUGIN_DIR/wow_context.json`, commonly `/home/deck/homebrew/plugins/decktation/wow_context.json`). Set `--output` to that file if you want the plugin to use the latest saved snapshot; the converter needs permission to write there.

For a single five-second recording with the standalone voice service, point it at the generated file with `--context`:

```bash
python3 backend/src/wow_voice_chat.py --context wow_context.json --mode once --duration 5
```

## Troubleshooting

- If the addon does not appear, confirm the directory contains `DecktationContext.toc`, enable it in WoW’s AddOns list, and reload the UI.
- If the converter cannot find the SavedVariables file, pass its full path with `--input`.
- If transcription does not use context, confirm the JSON file is current and located at the path used by the Decky plugin or standalone service.
- The context and transcript stay on the Steam Deck. See [Privacy and permissions](PRIVACY_AND_PERMISSIONS.md) for details about optional diagnostics.
