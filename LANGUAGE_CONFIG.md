# Multi-Language Channel Detection

Decktation now supports multi-language channel detection! You can say channel names in any configured language.

## How It Works

When you say:
- **English**: "party let's go" → sends `/p let's go`
- **French**: "groupe allons-y" → sends `/p allons-y`

The plugin:
1. Auto-detects the spoken language (no more forced English translation!)
2. Recognizes channel keywords from all enabled languages
3. Applies the correct WoW chat command

## Configuration File

Channel mappings are stored in `channel_languages.json`:

```json
{
  "languages": {
    "en": {
      "name": "English",
      "channels": {
        "party": ["party"],
        "say": ["say"],
        ...
      }
    },
    "fr": {
      "name": "Français",
      "channels": {
        "party": ["groupe", "party", "partie"],
        "say": ["dis", "dire", "dites"],
        ...
      }
    }
  },
  "channel_commands": {
    "party": "/p ",
    "say": "/s ",
    ...
  },
  "enabled_languages": ["en", "fr"],
  "default_channel": "say"
}
```

## Adding a New Language

To add Spanish support:

1. Open `channel_languages.json`
2. Add a new language section:

```json
"es": {
  "name": "Español",
  "channels": {
    "party": ["grupo", "party"],
    "raid": ["raid", "banda"],
    "guild": ["hermandad", "guild"],
    "officer": ["oficial", "officer"],
    "say": ["decir", "di"],
    "yell": ["gritar", "grita"],
    "instance": ["instancia"],
    "whisper": ["susurrar", "susurra"],
    "type": ["escribir", "escribe"]
  }
}
```

3. Enable the language:
```json
"enabled_languages": ["en", "fr", "es"]
```

4. Save and restart the plugin

## Supported Formats

The plugin recognizes these formats:
- `party hello` (space)
- `party: hello` (colon)
- `party, hello` (comma)
- `party. hello` (period)

All are case-insensitive: `Party`, `PARTY`, `party` all work.

## Verb Conjugations

For verb-based channels (say, yell, whisper, type), you can include multiple conjugations:

```json
"say": ["dis", "dire", "dites"]  // tu, infinitive, vous forms
```

This lets French speakers say:
- "dis bonjour" (informal)
- "dire bonjour" (infinitive)
- "dites bonjour" (formal)

All map to the same `/s` command.

## Testing

Run the test script to verify channel detection:

```bash
python3 test_channels.py
```

This tests both English and French channel detection without needing the full Whisper model installed.
