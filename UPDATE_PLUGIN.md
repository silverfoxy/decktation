# How to Update the Decky Plugin

This guide shows you how to update your installed Decktation plugin with the latest changes (button configuration, Midnight WoW addon, etc.).

## Quick Update (Recommended)

If you already have the plugin installed and want to update it:

```bash
# From the project directory
cd /home/deck/Documents/personal/decktation

# Copy updated files to Decky plugin directory
# Decky plugins are usually at one of these locations:
PLUGIN_DIR=~/.local/share/decky/plugins/decktation
# OR
PLUGIN_DIR=~/homebrew/plugins/decktation

# Copy all necessary files
rsync -av --exclude='node_modules' \
          --exclude='venv' \
          --exclude='.git' \
          --exclude='*.md' \
          --exclude='test_*.py' \
          --exclude='quick_test.sh' \
          . "$PLUGIN_DIR/"

# Restart Decky Loader (from Desktop Mode)
systemctl --user restart plugin_loader
```

## Manual Update (Step by Step)

### Step 1: Find Your Decky Plugin Directory

```bash
# Check which directory exists
ls -la ~/.local/share/decky/plugins/decktation
# OR
ls -la ~/homebrew/plugins/decktation
```

Use whichever path exists. For this guide, we'll use:
```bash
PLUGIN_DIR=~/homebrew/plugins/decktation
```

### Step 2: Backup Current Installation (Optional but Recommended)

```bash
cp -r "$PLUGIN_DIR" "${PLUGIN_DIR}.backup.$(date +%Y%m%d)"
```

### Step 3: Copy Core Files

From your development directory:

```bash
cd /home/deck/Documents/personal/decktation

# Copy Python backend files
cp main.py "$PLUGIN_DIR/"
cp controller_listener.py "$PLUGIN_DIR/"
cp wow_voice_chat.py "$PLUGIN_DIR/"
cp convert_wow_context.py "$PLUGIN_DIR/"

# Copy built frontend
cp dist/index.js "$PLUGIN_DIR/dist/"

# Copy setup scripts
cp install_deps.sh "$PLUGIN_DIR/"
cp setup_ydotoold.sh "$PLUGIN_DIR/"

# Copy metadata files
cp package.json "$PLUGIN_DIR/"
cp plugin.json "$PLUGIN_DIR/"  # if it exists
cp defaults.json "$PLUGIN_DIR/"  # if it exists
```

### Step 4: Copy WoW Addon (Optional)

If you use WoW integration:

```bash
cp -r WowAddon "$PLUGIN_DIR/"
```

### Step 5: Restart Decky Loader

**From Desktop Mode:**

```bash
systemctl --user restart plugin_loader
```

**From Game Mode:**

1. Open Quick Access Menu (... button)
2. Go to Decky settings
3. Choose "Restart Decky Loader"

OR just reboot your Steam Deck.

## Files to Copy - Complete List

### Required Files

These files **must** be copied for the plugin to work:

```
main.py                      # Backend plugin
controller_listener.py        # Button detection
wow_voice_chat.py            # Voice transcription
dist/index.js                # Built frontend UI
package.json                 # Metadata
```

### Important Files

These files are highly recommended:

```
install_deps.sh              # Dependency installer
setup_ydotoold.sh            # ydotool setup
convert_wow_context.py       # WoW context converter
```

### Optional Files

These are optional but useful:

```
WowAddon/                    # WoW addon (if you play WoW)
lib/                         # Python dependencies (if already installed)
button_config.json           # Your button settings (don't overwrite if exists!)
wow_context.json             # Your WoW context (don't overwrite if exists!)
```

### DO NOT Copy

**Don't copy these to the plugin directory:**

```
node_modules/                # Node dependencies (not needed in plugin)
venv/                        # Python venv (not needed)
.git/                        # Git repository
src/                         # TypeScript source (only dist/index.js needed)
*.md                         # Documentation
test_*.py                    # Test scripts
quick_test.sh                # Test script
```

## Verification

After updating, verify the plugin works:

### 1. Check Plugin Loads

```bash
# Check Decky logs
tail -f /tmp/decky*.log
```

Look for:
```
[Decktation] Plugin loaded successfully
```

### 2. Check Plugin UI

1. Switch to Game Mode (or stay in Desktop Mode)
2. Open Quick Access Menu (... button)
3. Find "Decktation" in plugin list
4. Should see:
   - Button 1 dropdown (default: L1)
   - Button 2 dropdown (default: R1)
   - "Hold L1+R1 to record" text
   - Enable Dictation toggle

### 3. Test Button Config

1. Change Button 1 to "L2"
2. Check that button_config.json is created:
   ```bash
   cat "$PLUGIN_DIR/button_config.json"
   # Should show: {"button1":"L2","button2":"R1"}
   ```

### 4. Check Logs

```bash
tail -f /tmp/decktation.log
```

Should see:
```
Decktation: ... INFO Initializing Decktation plugin
Decktation: ... INFO Controller listener starting
Decktation: ... INFO Button combo: L1+R1 (codes 310+311)
```

## Troubleshooting

### Plugin Won't Load

**Check file permissions:**
```bash
chmod +x "$PLUGIN_DIR/main.py"
chmod +x "$PLUGIN_DIR/controller_listener.py"
chmod +x "$PLUGIN_DIR/install_deps.sh"
```

**Check Python dependencies:**
```bash
ls -la "$PLUGIN_DIR/lib/"
# Should see: evdev, sounddevice, faster_whisper, etc.

# If missing, reinstall:
cd "$PLUGIN_DIR"
./install_deps.sh
```

### Button Config Not Showing

**Check frontend is updated:**
```bash
# Make sure you copied the NEW dist/index.js
stat "$PLUGIN_DIR/dist/index.js"

# Should show recent timestamp (today's date)
```

**Rebuild frontend if needed:**
```bash
cd /home/deck/Documents/personal/decktation
npm run build
cp dist/index.js "$PLUGIN_DIR/dist/"
```

### Controller Listener Fails

**Check evdev library:**
```bash
ls -la "$PLUGIN_DIR/lib/evdev"*
```

**Check listener script:**
```bash
python3 "$PLUGIN_DIR/controller_listener.py"
# Should show: "Controller listener starting..."
```

### Old UI Still Showing (Says "L5" instead of "L1+R1")

**Clear browser cache:**
```bash
# Restart Decky to force UI reload
systemctl --user restart plugin_loader
```

**Or force rebuild:**
```bash
cd /home/deck/Documents/personal/decktation
npm run build
cp dist/index.js "$PLUGIN_DIR/dist/"
systemctl --user restart plugin_loader
```

## Complete Update Script

Here's a complete script that does everything:

```bash
#!/bin/bash
# update_decktation_plugin.sh

set -e

echo "=== Decktation Plugin Updater ==="

# Find plugin directory
if [ -d ~/.local/share/decky/plugins/decktation ]; then
    PLUGIN_DIR=~/.local/share/decky/plugins/decktation
elif [ -d ~/homebrew/plugins/decktation ]; then
    PLUGIN_DIR=~/homebrew/plugins/decktation
else
    echo "Error: Decktation plugin directory not found!"
    echo "Please install the plugin first."
    exit 1
fi

echo "Plugin directory: $PLUGIN_DIR"

# Backup current installation
BACKUP_DIR="${PLUGIN_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
echo "Creating backup: $BACKUP_DIR"
cp -r "$PLUGIN_DIR" "$BACKUP_DIR"

# Source directory (where this script is)
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Source directory: $SOURCE_DIR"

# Copy files
echo "Copying files..."
cd "$SOURCE_DIR"

# Core files
cp main.py "$PLUGIN_DIR/"
cp controller_listener.py "$PLUGIN_DIR/"
cp wow_voice_chat.py "$PLUGIN_DIR/"
cp convert_wow_context.py "$PLUGIN_DIR/"
cp dist/index.js "$PLUGIN_DIR/dist/"
cp install_deps.sh "$PLUGIN_DIR/"
cp setup_ydotoold.sh "$PLUGIN_DIR/"
cp package.json "$PLUGIN_DIR/"

# Optional: WoW addon
if [ -d WowAddon ]; then
    echo "Copying WoW addon..."
    cp -r WowAddon "$PLUGIN_DIR/"
fi

# Preserve user config files (don't overwrite)
if [ ! -f "$PLUGIN_DIR/button_config.json" ]; then
    echo "No button config found (will use default L1+R1)"
fi

if [ ! -f "$PLUGIN_DIR/wow_context.json" ]; then
    echo "No WoW context found (will be created if needed)"
fi

# Set permissions
chmod +x "$PLUGIN_DIR/main.py"
chmod +x "$PLUGIN_DIR/controller_listener.py"
chmod +x "$PLUGIN_DIR/install_deps.sh"
chmod +x "$PLUGIN_DIR/setup_ydotoold.sh"

echo "Files copied successfully!"
echo ""
echo "Next steps:"
echo "1. Restart Decky Loader:"
echo "   systemctl --user restart plugin_loader"
echo "2. Open Quick Access and check Decktation plugin"
echo "3. Verify button dropdowns show L1, R1, etc."
echo ""
echo "Backup saved at: $BACKUP_DIR"
echo "To restore: mv \"$BACKUP_DIR\" \"$PLUGIN_DIR\""
```

Save this as `update_decktation_plugin.sh` and run:

```bash
chmod +x update_decktation_plugin.sh
./update_decktation_plugin.sh
```

## After Update - What's New?

You should now see:

1. **Button Configuration Dropdowns**
   - Button 1: Dropdown with 10 button options
   - Button 2: Dropdown with 10 button options
   - Default: L1+R1

2. **Updated Text**
   - "Hold L1+R1 to record" (instead of "Hold L5")
   - Help text mentions button combo is configurable

3. **Backend Improvements**
   - Button config saved to button_config.json
   - Controller listener reads config dynamically
   - Logs show actual button combo in use

4. **WoW Addon (if installed)**
   - Compatible with Midnight (12.0)
   - Modern C_Map API for zones
   - Backward compatible with War Within

## Keeping Updated

To update again in the future, just run:

```bash
cd /home/deck/Documents/personal/decktation
git pull  # if using git
./update_decktation_plugin.sh
```

## Full Fresh Install

If you prefer to completely reinstall (nuclear option):

```bash
# Remove old plugin
rm -rf ~/homebrew/plugins/decktation

# Copy new plugin
mkdir -p ~/homebrew/plugins/decktation
rsync -av --exclude='node_modules' \
          --exclude='venv' \
          --exclude='.git' \
          /home/deck/Documents/personal/decktation/ \
          ~/homebrew/plugins/decktation/

# Restart Decky
systemctl --user restart plugin_loader
```

## Need Help?

Check these logs if something goes wrong:

```bash
# Decky loader logs
tail -f /tmp/decky*.log

# Decktation plugin logs
tail -f /tmp/decktation.log

# Controller listener (appears in decktation.log)
grep "controller_listener" /tmp/decktation.log
```

Report issues with:
- Log output
- What you expected to happen
- What actually happened
- Steps to reproduce
