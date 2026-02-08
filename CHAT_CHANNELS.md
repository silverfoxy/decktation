# Chat Channel Support

The voice-to-text service now supports sending messages to different WoW chat channels!

## Quick Start

### Method 1: Set Default Channel

Use the `--channel` flag to set which chat channel to use by default:

```bash
# Send everything to party chat
python wow_voice_chat.py --channel party --mode once --duration 5

# Send everything to raid chat
python wow_voice_chat.py --channel raid --mode push-to-talk

# Send everything to guild chat
python wow_voice_chat.py --channel guild --mode once
```

### Method 2: Voice Prefix (Recommended!)

Say the channel name before your message:

```bash
python wow_voice_chat.py --mode once --duration 5
```

**Then say:**
- "**party** let's pull the boss"
- "**raid** stack for mechanics"
- "**guild** anyone want to run mythics?"
- "**say** hello there"

The service will automatically detect the channel and send to the right place!

### Method 3: Auto-Detection from Context

Use `--channel auto` to automatically choose based on your group:

```bash
python wow_voice_chat.py --channel auto --mode push-to-talk
```

**Auto-detection rules:**
- **In Raid** (6+ people): Uses `/raid` by default
- **In Party** (2-5 people): Uses `/p` by default
- **Solo**: Uses `/s` (say) by default

You can still override by saying the channel name first!

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

## Examples

### Example 1: Raid Communication

```bash
# Set default to raid
python wow_voice_chat.py --channel raid --mode push-to-talk --ptt-key '`'
```

Now when you record:
- "**stack on marker**" → Goes to `/raid stack on marker`
- "**lust on pull**" → Goes to `/raid lust on pull`
- "**say** ready?" → Goes to `/s ready?` (overridden to say)

### Example 2: Party Dungeons

```bash
# Auto-detect (will use party when in group)
python wow_voice_chat.py --channel auto --mode push-to-talk
```

Recording:
- "**pull the next pack**" → `/p pull the next pack` (auto-detected party)
- "**guild** anyone want to join us?" → `/g anyone want to join us?` (explicit override)

### Example 3: Multi-Channel Communication

```bash
# Default to say, but use voice prefixes to switch
python wow_voice_chat.py --mode push-to-talk
```

Recording different messages:
- "**say** hello" → `/s hello`
- "**party** ready to go" → `/p ready to go`
- "**raid** pull boss now" → `/raid pull boss now`
- "**guild** looking for more" → `/g looking for more`

### Example 4: Guild Recruitment

```bash
# Set default to guild
python wow_voice_chat.py --channel guild --mode continuous --duration 5
```

Everything goes to guild chat unless you specify otherwise.

## Voice Prefix Formats

The service recognizes these formats:

- `"party let's go"` → Sends to party
- `"party: let's go"` → Sends to party (with colon)
- `"PARTY let's go"` → Case insensitive

## Integration with Context

When using `--channel auto`, the service checks your WoW context:

```python
# If wow_context.json shows:
{
  "party": ["Player1", "Player2", "Player3", "Player4", "Player5"]
}

# Auto-detect will use party chat
```

```python
# If wow_context.json shows:
{
  "party": ["Player1", "Player2", ..., "Player15"]  # 15+ people
}

# Auto-detect will use raid chat
```

## Complete Usage Examples

### Scenario 1: Mythic+ Dungeon

You're running a Mythic+ with 4 friends:

```bash
# Terminal 1: Keep context updated
python convert_wow_context.py --watch

# Terminal 2: Voice with auto-detection
python wow_voice_chat.py --channel auto --context wow_context.json --mode push-to-talk
```

**Usage:**
- Hold `` ` `` and say: "**skip this pack**"
  - Auto-detects you're in a party → `/p skip this pack`
- Hold `` ` `` and say: "**guild who wants to run keys?**"
  - Explicit override → `/g who wants to run keys?`

### Scenario 2: Raid Night

You're in a 20-person raid:

```bash
python wow_voice_chat.py --channel raid --context wow_context.json --mode push-to-talk
```

**Usage:**
- Hold `` ` `` and say: "**stack for beam**"
  - Goes to `/raid stack for beam`
- Hold `` ` `` and say: "**officer need more healers**"
  - Overridden to `/o need more healers`

### Scenario 3: Solo Questing

You're questing alone but want to chat with guild:

```bash
python wow_voice_chat.py --channel guild --mode once --duration 5
```

**Usage:**
- Record: "**anyone want to help with this quest?**"
  - Goes to `/g anyone want to help with this quest?`

## Tips and Best Practices

### 1. Use Voice Prefixes for Flexibility

Even with a default channel set, you can override per-message:

```bash
# Default to party
python wow_voice_chat.py --channel party --mode push-to-talk

# But you can still say:
# - "raid move to safe spot" → Goes to raid
# - "guild need enchanter" → Goes to guild
# - "stack on me" → Goes to party (default)
```

### 2. Auto-Detection for Dynamic Groups

Use `--channel auto` if you switch between solo, party, and raid frequently:

```bash
python wow_voice_chat.py --channel auto --mode daemon
```

The service will automatically adjust based on your current group size.

### 3. Quick Channel Switching

Train yourself to say the channel name first:

- "**party**" + message
- "**raid**" + message
- "**guild**" + message

This becomes second nature quickly!

### 4. Combine with Context

The service loads your WoW context, so:

```bash
python wow_voice_chat.py --channel auto --context wow_context.json --mode push-to-talk
```

Now it knows:
- Your current zone (for better transcription)
- Your party/raid members
- Your class and spec
- And automatically picks the right chat channel!

## Testing

### Test Channel Detection

```bash
# Quick test
python wow_voice_chat.py --mode once --duration 5
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
  python wow_voice_chat.py --mode once --duration 3 --channel $channel
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

### Wrong channel auto-detected

**Problem:** Auto mode choosing wrong channel

**Solution:**
- Check your context: `cat wow_context.json`
- Verify party member count is correct
- Use explicit `--channel` instead of auto
- Or use voice prefixes to override

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
python wow_voice_chat.py --mode once --duration 5
```

**Say:** "whisper PlayerName hey want to group?"

**Result:** `/w PlayerName hey want to group?`

Note: You need to say the player name clearly for this to work!

## Summary

**Three ways to control channels:**

1. **Default flag**: `--channel party`
2. **Voice prefix**: Say "party" before your message
3. **Auto-detect**: `--channel auto` (uses context)

**Recommended setup for most users:**

```bash
# Keep context updated
python convert_wow_context.py --watch &

# Use auto-detection with voice overrides
python wow_voice_chat.py --channel auto --context wow_context.json --mode push-to-talk --ptt-key '`'
```

This gives you:
- Automatic channel selection based on group
- Context-aware transcription for WoW terms
- Ability to override with voice prefixes
- Push-to-talk for easy activation

Happy chatting!
