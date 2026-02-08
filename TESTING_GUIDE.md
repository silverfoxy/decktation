# WoW Voice Integration Testing Guide

This guide walks you through testing the complete integration between WoW addon and voice transcription.

## Quick Start

Run the automated test script:

```bash
cd /home/deck/Documents/personal/decktation
./test_wow_integration.sh
```

This will verify each component automatically.

## Manual Testing Steps

### Step 1: Verify WoW Addon is Saving Data

**In WoW:**
1. Make sure you're logged in to a character
2. Type `/decktation` in chat
3. You should see output like:

```
Decktation Context Exported:
  Zone: Dornogal
  Subzone: The Coreway
  Boss:
  Target:
  Party: YourCharacterName
  Class: WARRIOR
  Spec: Fury
```

**If it doesn't work:**
- Check addon is enabled in AddOns menu
- Type `/reload` to reload UI
- Check for errors: `/decktation errors`

### Step 2: Find SavedVariables File

The addon saves to:
```
WTF/Account/<ACCOUNT>/SavedVariables/DecktationContext.lua
```

**On Steam Deck with Proton:**

```bash
# Find it automatically
find ~/.local/share/Steam/steamapps/compatdata -name "DecktationContext.lua" 2>/dev/null
```

**Or manually check:**
```bash
# Example path (replace <appid> with your actual app ID)
ls ~/.local/share/Steam/steamapps/compatdata/<appid>/pfx/drive_c/Program\ Files\ \(x86\)/World\ of\ Warcraft/_retail_/WTF/Account/*/SavedVariables/DecktationContext.lua
```

**View the file:**
```bash
cat /path/to/DecktationContext.lua
```

Should show something like:
```lua
DecktationContextDB = {
    ["zone"] = "Dornogal",
    ["subzone"] = "The Coreway",
    ["boss"] = "",
    ["target"] = "",
    ["party"] = {
        "CharacterName",
    },
    ["class"] = "WARRIOR",
    ["spec"] = "Fury",
    ["timestamp"] = 1704312345,
}
```

### Step 3: Test Conversion Script

Convert the Lua SavedVariables to JSON:

```bash
cd /home/deck/Documents/personal/decktation

# Auto-detect SavedVariables location
python convert_wow_context.py

# Or specify manually
python convert_wow_context.py --input "/path/to/DecktationContext.lua"

# Check the output
cat wow_context.json
```

**Expected output:**
```json
{
  "zone": "Dornogal",
  "subzone": "The Coreway",
  "boss": "",
  "target": "",
  "party": [
    "CharacterName"
  ],
  "class": "WARRIOR",
  "spec": "Fury"
}
```

### Step 4: Test Voice Service with Context

Now test that the voice service loads and uses the context:

**Test 1: Verify context loading**

```bash
python3 << 'EOF'
from wow_voice_chat import WoWVoiceChat

service = WoWVoiceChat(context_file="wow_context.json")
service.load_context()

print("Loaded context:")
print(f"  Zone: {service.context.get('zone')}")
print(f"  Spec: {service.context.get('spec')}")

# Test prompt building
prompt, hotwords = service.build_prompt_from_context()
print(f"\nGenerated prompt:")
print(f"  {prompt[:100]}...")
print(f"\nHotwords: {hotwords}")
EOF
```

**Expected:** Should show your zone, spec, and a prompt with WoW terminology.

**Test 2: Quick voice test (no WoW needed)**

Create a test context to verify the voice service works:

```bash
# Create test context
cat > wow_context_test.json << 'EOF'
{
  "zone": "Icecrown Citadel",
  "subzone": "The Frozen Throne",
  "boss": "The Lich King",
  "target": "The Lich King",
  "party": ["TestPaladin", "TestPriest"],
  "class": "PALADIN",
  "spec": "Retribution"
}
EOF

# Test with voice service
python wow_voice_chat.py --context wow_context_test.json --mode once --duration 3
```

**During recording, say something WoW-related like:**
- "Let's pull the Lich King"
- "I'm playing retribution paladin"
- "Meet at Icecrown"

**Expected:** The transcription should correctly spell WoW-specific terms.

### Step 5: Full Integration Test

**Terminal 1: Run converter in watch mode**

```bash
cd /home/deck/Documents/personal/decktation

# Find your SavedVariables path from Step 2
SAVED_VARS="/path/to/DecktationContext.lua"

# Run in watch mode
python convert_wow_context.py --input "$SAVED_VARS" --watch
```

This will automatically update `wow_context.json` when the SavedVariables file changes.

**Terminal 2: Run voice service**

```bash
cd /home/deck/Documents/personal/decktation

# Option A: Test once
python wow_voice_chat.py --context wow_context.json --mode once --duration 5

# Option B: Push-to-talk mode (hold ` key to record)
python wow_voice_chat.py --context wow_context.json --mode push-to-talk --ptt-key '`'

# Option C: Daemon mode (for Decky integration)
python wow_voice_chat.py --context wow_context.json --mode daemon
```

**Test the integration:**

1. **In WoW:** Go to a recognizable zone (like Dorgal, Icecrown, etc.)
2. **Wait 2 seconds** for addon to update SavedVariables
3. **Check Terminal 1:** Should show "File changed, converting..."
4. **In Terminal 2:** Record some voice (or trigger recording)
5. **Say WoW-specific terms** from your current zone
6. **Check transcription:** Should correctly recognize zone names, etc.

### Step 6: Test Context Updates

Test that context updates as you play:

1. **Start both terminals** (converter watch + voice service)
2. **In WoW, change zones**
   - Watch Terminal 1 update the context
3. **Target a boss or elite mob**
   - Should appear in boss/target fields
4. **Join a party**
   - Party members should appear
5. **Use `/decktation` in WoW**
   - Verify the data matches what's in wow_context.json

## Troubleshooting

### SavedVariables not found

**Problem:** Can't find DecktationContext.lua

**Solutions:**
1. Make sure addon is installed in `Interface/AddOns/DecktationContext/`
2. Log in to WoW with a character
3. Type `/decktation` to verify addon is loaded
4. Log out or `/reload` (forces SavedVariables write)
5. Search manually:
   ```bash
   find ~ -name "DecktationContext.lua" 2>/dev/null
   ```

### Context not updating

**Problem:** wow_context.json stays the same

**Solutions:**
1. Check converter watch mode is running
2. In WoW, force update: `/reload` or log out
3. Verify SavedVariables file timestamp is updating:
   ```bash
   ls -lh /path/to/DecktationContext.lua
   ```
4. Check converter has write permissions:
   ```bash
   ls -lh wow_context.json
   ```

### Voice service not using context

**Problem:** Still getting misspelled WoW terms

**Solutions:**
1. Verify context file exists: `cat wow_context.json`
2. Check the prompt being generated:
   ```python
   from wow_voice_chat import WoWVoiceChat
   s = WoWVoiceChat(context_file="wow_context.json")
   s.load_context()
   print(s.build_prompt_from_context())
   ```
3. Make sure context has meaningful data (zone, boss, etc.)
4. Try saying terms that are IN your current context

### Transcription still wrong

**Problem:** WoW terms still misspelled even with context

**Things to try:**
1. **Speak clearly** - Whisper isn't magic
2. **Use terms from your current context** - Context helps most with current zone/boss
3. **Check your context has data**:
   ```bash
   cat wow_context.json
   ```
4. **Test with known context:**
   - Go to well-known zone (Orgrimmar, Stormwind)
   - Say the zone name
   - Should recognize it better
5. **Increase model size** - Edit wow_voice_chat.py line 27:
   ```python
   # Change from "base" to "small" for better accuracy
   self.model = WhisperModel("small", device="cpu", compute_type="int8")
   ```

### Performance issues

**Problem:** Voice service is slow

**Solutions:**
1. **Use smaller model** - Edit wow_voice_chat.py:
   ```python
   self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
   ```
2. **Reduce recording duration**:
   ```bash
   python wow_voice_chat.py --duration 3  # Instead of 5
   ```
3. **Check CPU usage:**
   ```bash
   htop
   ```

## Advanced Testing

### Test with fake data

Create various context scenarios:

```bash
# Boss fight scenario
cat > test_raid.json << 'EOF'
{
  "zone": "Icecrown Citadel",
  "boss": "The Lich King",
  "party": ["Tank1", "Healer1", "DPS1", "DPS2", "DPS3"],
  "spec": "Holy",
  "class": "PRIEST"
}
EOF

python wow_voice_chat.py --context test_raid.json --mode once --duration 3
# Say: "Lich King is at 50 percent health"

# Dungeon scenario
cat > test_dungeon.json << 'EOF'
{
  "zone": "The Necrotic Wake",
  "subzone": "Zolramus",
  "target": "Surgeon Stitchflesh",
  "party": ["Tank", "Healer", "DPS1", "DPS2", "DPS3"],
  "spec": "Protection",
  "class": "PALADIN"
}
EOF

python wow_voice_chat.py --context test_dungeon.json --mode once --duration 3
# Say: "Pull Stitchflesh when ready"
```

### Measure improvement

Compare with and without context:

```bash
# Without context
python wow_voice_chat.py --mode once --duration 3
# Say: "The Lich King"

# With context
python wow_voice_chat.py --context test_raid.json --mode once --duration 3
# Say: "The Lich King"
```

Compare the transcriptions!

## Success Criteria

You know it's working when:

1. ✅ `/decktation` in WoW shows current context
2. ✅ SavedVariables file exists and has recent data
3. ✅ `wow_context.json` updates when you change zones
4. ✅ Voice service loads context without errors
5. ✅ WoW-specific terms are transcribed correctly
6. ✅ Transcription improves when context matches what you say

## Next Steps

Once testing works:

1. **Set up automation** - Use systemd service or launch script
2. **Integrate with Decky** - Use daemon mode for Steam Deck UI
3. **Create keybinds** - Map controller buttons for push-to-talk
4. **Fine-tune prompts** - Edit wow_voice_chat.py to add more WoW vocabulary

## Getting Help

If you're stuck:

1. Run `./test_wow_integration.sh` and share the output
2. Check error logs: `/decktation errors` in WoW
3. Check Python logs in terminal
4. Verify each component works individually before testing together
