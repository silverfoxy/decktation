# Chat Channel Support

The voice-to-text service now supports sending messages to different WoW chat channels!

Standalone modes are `once`, `continuous`, and `daemon`. For controller push-to-talk, use the Decky plugin; standalone keyboard push-to-talk is no longer supported.

## Quick Start

### Method 1: Set Default Channel

Use the `--channel` flag to set which chat channel to use by default:

```bash
# Send everything to party chat
python3 backend/src/wow_voice_chat.py --channel party --mode once --duration 5

# Send everything to raid chat
python3 backend/src/wow_voice_chat.py --channel raid --mode once --duration 5

# Send everything to guild chat
python3 backend/src/wow_voice_chat.py --channel guild --mode once
```

### Method 2: Voice Prefix (Recommended!)

Say the channel name before your message:

```bash
python3 backend/src/wow_voice_chat.py --mode once --duration 5
```

**Then say:**
- "**party** let's pull the boss"
- "**raid** stack for mechanics"
- "**guild** anyone want to run mythics?"
- "**say** hello there"

A spoken channel prefix selects that message’s destination; without a prefix, the selected default channel is used.

## Supported Channels

| Channel | Command | Voice Prefix | Description |
|---------|---------|--------------|-------------|
| **say** | `/s` | "say" | Local area chat |
| **party** | `/p` | "party" | Party chat |
| **raid** | `/raid` | "raid" | Raid chat |
| **guild** | `/g` | "guild" | Guild chat |
| **officer** | `/o` | "officer" | Officer chat |
| **yell** | `/y` | "yell" | Yell (larger area) |
| **instance** | `/i` | "instance" | Instance chat |
| **channel 1–5** | `/1`–`/5` | "channel one"–"channel five" (or "channel 1"–"channel 5") | Numbered chat channels currently joined in WoW |

Numbered channel slots depend on the channels joined by your character; verify them in-game with `/chatlist`. Use the explicit "channel N" prefix so ordinary words such as "trade" are not mistaken for a routing command.

## Examples

### Example 1: Raid Communication

```bash
# Set default to raid
python3 backend/src/wow_voice_chat.py --channel raid --mode once --duration 5
```

Now when you record:
- "**stack on marker**" → Goes to `/raid stack on marker`
- "**lust on pull**" → Goes to `/raid lust on pull`
- "**say** ready?" → Goes to `/s ready?` (overridden to say)

### Example 2: Party Dungeons

```bash
# Default to party chat
python3 backend/src/wow_voice_chat.py --channel party --mode once --duration 5
```

Recording:
- "**pull the next pack**" → `/p pull the next pack`
- "**guild** anyone want to join us?" → `/g anyone want to join us?` (explicit override)

### Example 3: Multi-Channel Communication

```bash
# Default to say, but use voice prefixes to switch
python3 backend/src/wow_voice_chat.py --mode once --duration 5
```

Recording different messages:
- "**say** hello" → `/s hello`
- "**party** ready to go" → `/p ready to go`
- "**raid** pull boss now" → `/raid pull boss now`
- "**guild** looking for more" → `/g looking for more`

### Example 4: Guild Recruitment

```bash
# Set default to guild
python3 backend/src/wow_voice_chat.py --channel guild --mode continuous --duration 5
```

Everything goes to guild chat unless you specify otherwise.

## Voice Prefix Formats

The service recognizes these formats:

- `"party let's go"` → Sends to party
- `"party: let's go"` → Sends to party (with colon)
- `"PARTY let's go"` → Case insensitive

## Integration with Context

The WoW context can improve transcription of game terms. Select the destination separately with `--channel` or a spoken channel prefix. Context does not choose a chat channel.

## Complete Usage Examples

### Scenario 1: Mythic+ Dungeon

You're running a Mythic+ with 4 friends and choose party chat:

```bash
# Terminal 1: Keep context updated
python3 backend/src/convert_wow_context.py --watch

# Terminal 2: Voice with party chat and WoW context
python3 backend/src/wow_voice_chat.py --channel party --context wow_context.json --mode once --duration 5
```

**Usage:**
- Say: "**skip this pack**"
  - Uses the selected default `/p` channel
- Say: "**guild who wants to run keys?**"
  - Explicit override → `/g who wants to run keys?`

### Scenario 2: Raid Night

You're in a 20-person raid:

```bash
python3 backend/src/wow_voice_chat.py --channel raid --context wow_context.json --mode once --duration 5
```

**Usage:**
- Say: "**stack for beam**"
  - Goes to `/raid stack for beam`
- Say: "**officer need more healers**"
  - Overridden to `/o need more healers`

### Scenario 3: Solo Questing

You're questing alone but want to chat with guild:

```bash
python3 backend/src/wow_voice_chat.py --channel guild --mode once --duration 5
```

**Usage:**
- Record: "**anyone want to help with this quest?**"
  - Goes to `/g anyone want to help with this quest?`

## Tips and Best Practices

### 1. Use Voice Prefixes for Flexibility

Even with a default channel set, you can override per-message:

```bash
# Default to party
python3 backend/src/wow_voice_chat.py --channel party --mode once --duration 5

# But you can still say:
# - "raid move to safe spot" → Goes to raid
# - "guild need enchanter" → Goes to guild
# - "stack on me" → Goes to party (default)
```

### 2. Choose a Default for Each Session

Set `--channel` to the destination you want, then use a spoken channel prefix when a message needs a different destination.

### 3. Quick Channel Switching

Train yourself to say the channel name first:

- "**party**" + message
- "**raid**" + message
- "**guild**" + message

This becomes second nature quickly!

### 4. Combine with Context

The service loads your WoW context, so:

```bash
python3 backend/src/wow_voice_chat.py --channel party --context wow_context.json --mode once --duration 5
```

Now it knows:
- Your current zone (for better transcription)
- Your party/raid members
- Your class and spec

Choose the chat destination with `--channel` or a spoken prefix.

## Testing

### Test Channel Detection

```bash
# Quick test
python3 backend/src/wow_voice_chat.py --mode once --duration 5
```

**Say:** "party this is a test"

**Expected output:**
```
Transcribed: party this is a test
Sending to party: this is a test
```

### Test Different Channels

```bash
# Test each channel
for channel in say party raid guild; do
  echo "Testing $channel..."
  python3 backend/src/wow_voice_chat.py --mode once --duration 3 --channel $channel
  # Say something
done
```

## Troubleshooting

### Channel not being detected

**Problem:** Saying "party hello" but it goes to say chat

**Solution:**
- Make sure you're using the exact channel name
- Check the transcription output - did it hear "party" correctly?
- Channel names are: say, party, raid, guild, officer, yell, instance

### Message not sending

**Problem:** Transcription works but message doesn't appear in WoW

**Solution:**
- Make sure WoW window has focus
- Check if you're in a channel (e.g., can't use `/p` when solo)
- Try with `--channel say` first to test
- Verify xdotool is working: `xdotool type "test"`

## Advanced: Whisper Support

For whispers, use the voice prefix format:

```bash
python3 backend/src/wow_voice_chat.py --mode once --duration 5
```

**Say:** "whisper PlayerName hey want to group?"

**Result:** `/w PlayerName hey want to group?`

Note: You need to say the player name clearly for this to work!

To answer the last person who whispered you, say the **reply** prefix instead. No player name is
needed, because the game sends it to the most recent whisper conversation:

```bash
python3 backend/src/wow_voice_chat.py --mode once --duration 5
```

**Say:** "reply yeah let's run it"

**Result:** `/r yeah let's run it`

The game reports "There is nobody to reply to" when you have not received a whisper yet.

## Summary

**Two ways to choose a channel:**

1. **Default flag**: `--channel party`
2. **Voice prefix**: Say "party" before your message

**Recommended setup for most users:**

```bash
# Keep context updated
python3 backend/src/convert_wow_context.py --watch &

# Use party as default with voice prefix overrides
python3 backend/src/wow_voice_chat.py --channel party --context wow_context.json --mode once --duration 5
```

This gives you:
- Context-aware transcription for WoW terms
- Ability to override with voice prefixes
- A single five-second recording per invocation

Happy chatting!
