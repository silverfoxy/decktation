#!/bin/bash
# Quick test of voice-to-text with WoW context

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Quick WoW Voice Integration Test"
echo "=================================="
echo ""

# Check if we have a saved path
if [ -f ".wow_savedvars_path" ]; then
    SAVED_VARS=$(cat .wow_savedvars_path)
    echo "Using saved WoW SavedVariables path:"
    echo "  $SAVED_VARS"
    echo ""
else
    echo "Searching for WoW SavedVariables..."
    SAVED_VARS=$(find ~/.local/share/Steam/steamapps/compatdata -name "DecktationContext.lua" 2>/dev/null | head -1)

    if [ -z "$SAVED_VARS" ]; then
        echo "Error: Could not find DecktationContext.lua"
        echo ""
        echo "Please run ./test_wow_integration.sh first"
        exit 1
    fi

    echo "$SAVED_VARS" > .wow_savedvars_path
fi

# Convert latest context
echo "Converting WoW context..."
python convert_wow_context.py --input "$SAVED_VARS" --output wow_context.json

if [ ! -f "wow_context.json" ]; then
    echo "Error: Conversion failed"
    exit 1
fi

echo ""
echo "Current WoW context:"
echo "-------------------"
cat wow_context.json | python3 -m json.tool
echo ""

# Offer test options
echo "Choose test mode:"
echo "  1) Quick test (5 second recording)"
echo "  2) Push-to-talk (hold \` key)"
echo "  3) Watch mode (auto-update context)"
echo "  4) Just show context (no voice test)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Recording for 5 seconds... speak now!"
        echo "Try saying WoW-specific terms from your current zone/spec"
        echo ""
        python wow_voice_chat.py --context wow_context.json --mode once --duration 5
        ;;
    2)
        echo ""
        echo "Push-to-talk mode active"
        echo "Hold \` key to record, release to transcribe"
        echo "Press Ctrl+C to stop"
        echo ""
        python wow_voice_chat.py --context wow_context.json --mode push-to-talk --ptt-key '`'
        ;;
    3)
        echo ""
        echo "Watch mode - will auto-update context as you play WoW"
        echo ""
        echo "In a new terminal, run:"
        echo "  python wow_voice_chat.py --context wow_context.json --mode daemon"
        echo ""
        echo "Press Ctrl+C to stop watching"
        echo ""
        python convert_wow_context.py --input "$SAVED_VARS" --watch
        ;;
    4)
        echo ""
        echo "Context loaded successfully!"
        echo "To test voice, run this script again and choose option 1 or 2"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
