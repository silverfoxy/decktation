#!/bin/bash
# Test WoW Integration with Voice-to-Text
# This script helps verify each step of the integration

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "WoW Integration Test"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Find SavedVariables
echo -e "${YELLOW}Step 1: Finding WoW SavedVariables${NC}"
echo "Searching for DecktationContext.lua..."

SAVED_VARS_PATH=$(find ~/.local/share/Steam/steamapps/compatdata -name "DecktationContext.lua" 2>/dev/null | head -1)

if [ -z "$SAVED_VARS_PATH" ]; then
    echo -e "${RED}✗ SavedVariables not found!${NC}"
    echo ""
    echo "Please ensure:"
    echo "  1. WoW addon is installed in Interface/AddOns/"
    echo "  2. You've logged in at least once with the addon enabled"
    echo "  3. You've logged out or used /reload in-game"
    echo ""
    echo "You can also manually specify the path:"
    echo "  SAVED_VARS_PATH=/path/to/DecktationContext.lua $0"
    exit 1
else
    echo -e "${GREEN}✓ Found SavedVariables:${NC}"
    echo "  $SAVED_VARS_PATH"
fi

echo ""

# Step 2: Verify SavedVariables content
echo -e "${YELLOW}Step 2: Checking SavedVariables content${NC}"

if [ ! -f "$SAVED_VARS_PATH" ]; then
    echo -e "${RED}✗ File doesn't exist${NC}"
    exit 1
fi

FILE_SIZE=$(stat -c%s "$SAVED_VARS_PATH" 2>/dev/null || stat -f%z "$SAVED_VARS_PATH" 2>/dev/null || echo "0")

if [ "$FILE_SIZE" -lt 50 ]; then
    echo -e "${RED}✗ File is too small (${FILE_SIZE} bytes)${NC}"
    echo "  The addon may not have saved data yet"
    exit 1
fi

echo -e "${GREEN}✓ SavedVariables file looks good (${FILE_SIZE} bytes)${NC}"
echo ""
echo "Preview:"
head -20 "$SAVED_VARS_PATH"
echo ""

# Step 3: Test conversion script
echo -e "${YELLOW}Step 3: Testing conversion script${NC}"

if [ ! -f "convert_wow_context.py" ]; then
    echo -e "${RED}✗ convert_wow_context.py not found${NC}"
    exit 1
fi

echo "Running: python convert_wow_context.py --input \"$SAVED_VARS_PATH\" --output wow_context.json"
python convert_wow_context.py --input "$SAVED_VARS_PATH" --output wow_context.json

if [ ! -f "wow_context.json" ]; then
    echo -e "${RED}✗ Conversion failed - wow_context.json not created${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Conversion successful${NC}"
echo ""
echo "Generated wow_context.json:"
cat wow_context.json
echo ""

# Step 4: Verify JSON is valid
echo -e "${YELLOW}Step 4: Validating JSON${NC}"

python3 -c "import json; json.load(open('wow_context.json'))" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ JSON is valid${NC}"
else
    echo -e "${RED}✗ JSON is invalid${NC}"
    exit 1
fi

echo ""

# Step 5: Check voice service can load it
echo -e "${YELLOW}Step 5: Testing voice service context loading${NC}"

python3 << 'EOF'
import json
import sys

try:
    with open('wow_context.json') as f:
        context = json.load(f)

    print("\033[0;32m✓ Voice service can read context\033[0m")
    print("\nContext data:")
    print(f"  Zone: {context.get('zone', 'N/A')}")
    print(f"  Subzone: {context.get('subzone', 'N/A')}")
    print(f"  Boss: {context.get('boss', 'N/A')}")
    print(f"  Target: {context.get('target', 'N/A')}")
    print(f"  Party: {', '.join(context.get('party', []))}")
    print(f"  Class: {context.get('class', 'N/A')}")
    print(f"  Spec: {context.get('spec', 'N/A')}")

    # Check if we have meaningful context
    has_context = bool(context.get('zone') or context.get('boss') or context.get('party'))

    if has_context:
        print("\n\033[0;32m✓ Context has meaningful data\033[0m")
    else:
        print("\n\033[1;33m⚠ Context is mostly empty - this is OK if you just installed the addon\033[0m")
        print("  Play WoW for a bit and the context will populate")

except Exception as e:
    print(f"\033[0;31m✗ Error reading context: {e}\033[0m")
    sys.exit(1)
EOF

echo ""

# Step 6: Check dependencies for voice service
echo -e "${YELLOW}Step 6: Checking voice service dependencies${NC}"

python3 << 'EOF'
import sys

missing = []

try:
    import faster_whisper
    print("\033[0;32m✓ faster-whisper installed\033[0m")
except ImportError:
    print("\033[0;31m✗ faster-whisper not installed\033[0m")
    missing.append("faster-whisper")

try:
    import sounddevice
    print("\033[0;32m✓ sounddevice installed\033[0m")
except ImportError:
    print("\033[0;31m✗ sounddevice not installed\033[0m")
    missing.append("sounddevice")

try:
    import numpy
    print("\033[0;32m✓ numpy installed\033[0m")
except ImportError:
    print("\033[0;31m✗ numpy not installed\033[0m")
    missing.append("numpy")

if missing:
    print(f"\n\033[1;33mTo install missing dependencies:\033[0m")
    print(f"  pip install {' '.join(missing)}")
    sys.exit(1)
EOF

echo ""

# Summary
echo "========================================="
echo -e "${GREEN}Integration Test Complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. To run voice service once:"
echo "   python wow_voice_chat.py --context wow_context.json --mode once --duration 5"
echo ""
echo "2. To run in continuous watch mode:"
echo "   # Terminal 1:"
echo "   python convert_wow_context.py --input \"$SAVED_VARS_PATH\" --watch"
echo ""
echo "   # Terminal 2:"
echo "   python wow_voice_chat.py --context wow_context.json --mode daemon"
echo ""
echo "3. To run push-to-talk mode:"
echo "   python wow_voice_chat.py --context wow_context.json --mode push-to-talk --ptt-key '`'"
echo ""
echo "SavedVariables path saved for future use:"
echo "$SAVED_VARS_PATH" > .wow_savedvars_path
echo ""
