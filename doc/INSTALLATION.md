# Decktation Installation Guide

Complete installation guide for the Decktation push-to-talk dictation plugin for Steam Deck.

## Prerequisites

### 1. Decky Loader

Decky Loader must be installed on your Steam Deck. If you don't have it:

1. Visit https://deckbrew.xyz
2. Follow the installation instructions
3. Verify Decky is working by opening Quick Access Menu (... button)

### 2. ydotool Setup

Decktation uses ydotool to simulate keyboard input. **As of the latest version, ydotool is bundled with the plugin** - no separate installation needed!

For manual/development installations, you can optionally build ydotool:

#### Automated Setup (Recommended)

```bash
# Switch to Desktop Mode
# Open Konsole terminal
cd ~/Documents/personal/decktation
sudo ./setup_ydotoold.sh
```

This script:
- Checks for bundled ydotool binaries
- Offers to build ydotool from source if not found
- Creates a systemd service for ydotoold
- Sets proper permissions for /tmp/.ydotool_socket
- Enables the service to start on boot

#### Verify ydotoold is Running

```bash
pgrep ydotoold
# Should output a process ID number

# Or check the service status
systemctl --user status ydotoold
```

#### Manual Build (Alternative)

If you want to build ydotool separately:

```bash
# Build ydotool from source
cd ~/Documents/personal/decktation
./build_ydotool.sh

# Then set up the service
sudo ./setup_ydotoold.sh
```

The build script will:
- Clone ydotool from GitHub
- Compile it with cmake
- Place binaries in the `bin/` folder
- These will be bundled when you install the plugin

## Installation Methods

### Method 1: Install from Decky Plugin Store (Future)

Once published to the Decky Plugin Store:

1. Open Quick Access Menu (... button)
2. Navigate to Decky Plugin Store
3. Search for "Decktation"
4. Click Install
5. Wait for installation to complete

### Method 2: Install from URL (GitHub)

1. Open Quick Access Menu (... button)
2. Navigate to Decky settings
3. Select "Install from URL"
4. Enter: `https://github.com/silverfoxy/decktation`
5. Wait for installation to complete

### Method 3: Manual Installation

#### From Source (Development)

```bash
# Clone the repository
cd ~/Documents/personal
git clone https://github.com/silverfoxy/decktation.git
cd decktation

# Install Node dependencies
npm install

# Build the frontend
npm run build

# Install Python dependencies to lib folder
./install_deps.sh

# Copy to Decky plugins directory
mkdir -p ~/.local/share/decky/plugins
cp -r ~/Documents/personal/decktation ~/.local/share/decky/plugins/

# Restart Decky Loader
# Switch to Game Mode, open Quick Access, you should see Decktation
```

#### From Release Archive

```bash
# Download the latest release
cd ~/Downloads
wget https://github.com/silverfoxy/decktation/releases/latest/download/decktation.zip

# Extract
unzip decktation.zip

# Copy to Decky plugins directory
mkdir -p ~/.local/share/decky/plugins
cp -r decktation ~/.local/share/decky/plugins/

# Restart Decky Loader
```

## First Time Setup

### 1. Open the Plugin

1. Switch to Game Mode (or stay in Desktop Mode)
2. Open Quick Access Menu (... button)
3. Find "Decktation" in the plugin list
4. Click to open

### 2. Wait for Dependencies

On first open, the plugin will:

1. Show "Initializing service..." (a few seconds)
2. Dependencies are already installed in the `lib/` folder
3. Ready to use!

### 3. Load Whisper Model

The Whisper AI model loads on-demand:

1. Toggle "Enable Dictation" to ON
2. Plugin will show "Loading Whisper model..." (~5-10 seconds)
3. Model downloads from HuggingFace (one-time, ~150MB)
4. Once loaded, status shows "Ready"

### 4. Configure Buttons (Optional)

Default button combo is **L1+R1** (both bumpers):

1. In the plugin UI, you'll see two dropdowns:
   - **Button 1**: L1 (Left Bumper)
   - **Button 2**: R1 (Right Bumper)

2. To change, select different buttons from the dropdowns
3. The combo updates immediately
4. Try different combinations to find what works for you

**Recommended combos:**
- **L1+R1** (default) - Easy to press, doesn't interfere with most games
- **L2+R2** - Good if you don't use triggers for other functions
- **A+B** - Face buttons, easy to reach

**Avoid:**
- **L5+R5** - Often intercepted by Steam, may not work

## Testing

### Test 1: Manual Test Button

1. Enable dictation in the plugin
2. Wait for "Ready" status
3. Click "Start Test Recording"
4. Speak clearly: "This is a test"
5. Click "Stop Test Recording"
6. Check if text appears in active window

### Test 2: Controller Button Combo

1. Enable dictation
2. Make sure a text field is active (e.g., Steam chat, browser search bar)
3. Press and hold **L1+R1** (or your configured combo)
4. Plugin should show "Recording..." status
5. Speak: "Hello world"
6. Release buttons
7. Plugin shows "Transcribing..."
8. Text should appear: "hello world"

### Test 3: WoW Integration (If using WoW addon)

See `WOW_INTEGRATION.md` for full WoW setup.

## Troubleshooting

### Issue: Plugin doesn't show up

**Possible causes:**
- Decky Loader not installed
- Plugin files not in correct location
- Decky needs restart

**Solutions:**
```bash
# Check plugin location
ls -la ~/.local/share/decky/plugins/decktation

# Check Decky logs
tail -f /tmp/decky*.log

# Restart Decky (from Desktop Mode)
systemctl --user restart plugin_loader
```

### Issue: "Service not initialized"

**Possible causes:**
- Python dependencies missing
- Import errors in backend

**Solutions:**
```bash
# Check Decktation logs
tail -f /tmp/decktation.log

# Verify dependencies installed
ls -la ~/homebrew/plugins/decktation/lib/

# Re-run dependency installation
cd ~/homebrew/plugins/decktation
./install_deps.sh
```

### Issue: Recording doesn't start

**Possible causes:**
- Button combo not detected
- Controller listener not running
- ydotoold not running

**Solutions:**
```bash
# Check ydotoold
pgrep ydotoold
# If not running:
systemctl --user start ydotoold

# Check controller listener
pgrep -f controller_listener
# Should show a process ID

# Check logs
tail -f /tmp/decktation.log
# Look for "Controller listener starting"

# Try a different button combo
# Open plugin UI, change Button 1/Button 2
```

### Issue: Text doesn't appear after transcription

**Possible causes:**
- ydotoold not running
- Wrong window focused
- Permission issues

**Solutions:**
```bash
# Verify ydotoold is running
pgrep ydotoold

# Check ydotool permissions
ls -la /tmp/.ydotool_socket

# Test ydotool manually
ydotool type "test"
# Should type "test" in active window

# Restart ydotoold
systemctl --user restart ydotoold
```

### Issue: Transcription is inaccurate

**Possible causes:**
- Noisy environment
- Speaking too fast
- Whisper model too small
- No context for specialized terms

**Solutions:**
1. Speak clearly and at moderate pace
2. Use a headset microphone for better quality
3. Add context for specialized terms (see WoW integration)
4. Consider upgrading to larger model (edit `wow_voice_chat.py` line 28):
   ```python
   # Change from "base" to "small" for better accuracy
   self.model = WhisperModel("small", device="cpu", compute_type="int8")
   ```

### Issue: Plugin is slow or laggy

**Possible causes:**
- Steam Deck under load
- Large Whisper model
- Long recordings

**Solutions:**
1. Use smaller model for speed (edit `wow_voice_chat.py`):
   ```python
   # Change to "tiny" for faster processing
   self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
   ```
2. Keep recordings short (< 5 seconds)
3. Close other demanding apps

## Uninstallation

### Remove Plugin

```bash
# From Desktop Mode
rm -rf ~/.local/share/decky/plugins/decktation

# Restart Decky
systemctl --user restart plugin_loader
```

### Remove ydotoold (Optional)

```bash
# Stop and disable service
systemctl --user stop ydotoold
systemctl --user disable ydotoold

# Remove service file
rm ~/.config/systemd/user/ydotoold.service

# Uninstall ydotool package (optional)
sudo pacman -R ydotool
```

## Advanced Configuration

### Change Whisper Model

Edit `~/homebrew/plugins/decktation/wow_voice_chat.py` line ~28:

```python
# Options: "tiny", "base", "small", "medium", "large"
# Larger = more accurate but slower
self.model = WhisperModel("base", device="cpu", compute_type="int8")
```

### Add Custom Context

Create `~/homebrew/plugins/decktation/wow_context.json`:

```json
{
  "keywords": ["custom", "term", "list"],
  "vocabulary": ["specialized", "words"]
}
```

This helps Whisper recognize domain-specific terms.

### View Logs

```bash
# Decktation plugin logs
tail -f /tmp/decktation.log

# Decky Loader logs
tail -f /tmp/decky*.log

# Controller listener logs (via plugin log)
grep "controller_listener" /tmp/decktation.log
```

## Getting Help

1. Check logs: `/tmp/decktation.log`
2. Run test scripts: `./quick_test.sh`
3. Report issues: https://github.com/silverfoxy/decktation/issues
4. Include:
   - Error messages from logs
   - Steam Deck model and OS version
   - Steps to reproduce the issue

## Privacy & Security

- All voice processing happens **locally** on your Steam Deck
- No data sent to external servers
- Whisper model downloads from HuggingFace (one-time, ~150MB)
- Transcribed text is typed directly into active window
- No recordings are saved to disk (unless explicitly configured)

## What's Next?

- Read `CLAUDE.md` for technical details
- Check `WOW_INTEGRATION.md` for World of Warcraft setup
- See `TESTING_GUIDE.md` for comprehensive testing
- Review `CHAT_CHANNELS.md` for WoW chat channel commands

Enjoy dictation on your Steam Deck!
