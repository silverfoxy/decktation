#!/bin/bash
# Test chat channel functionality

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Chat Channel Feature Test"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}This script helps you test the chat channel feature${NC}"
echo ""
echo "Available channels:"
echo "  - say (local area)"
echo "  - party"
echo "  - raid"
echo "  - guild"
echo "  - officer"
echo "  - yell"
echo "  - instance"
echo ""

echo "Choose a test:"
echo "  1) Test specific channel (e.g., party chat)"
echo "  2) Test voice prefix detection (say 'party hello')"
echo "  3) Test auto-detection from context"
echo "  4) Interactive channel demo"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Available channels: say, party, raid, guild, officer, yell, instance"
        read -p "Enter channel to test: " channel

        echo ""
        echo -e "${GREEN}Recording 5 seconds to $channel chat...${NC}"
        echo "Say your message now (e.g., 'hello everyone')"
        echo ""

        python wow_voice_chat.py --channel "$channel" --mode once --duration 5
        ;;

    2)
        echo ""
        echo -e "${GREEN}Testing voice prefix detection${NC}"
        echo ""
        echo "Recording 5 seconds..."
        echo "Say: '<channel> <message>'"
        echo ""
        echo "Examples:"
        echo "  - 'party let's go'"
        echo "  - 'raid pull boss'"
        echo "  - 'guild anyone want to run dungeons?'"
        echo ""

        python wow_voice_chat.py --mode once --duration 5
        ;;

    3)
        echo ""
        echo -e "${GREEN}Testing auto-detection from context${NC}"
        echo ""

        # Check if context exists
        if [ ! -f "wow_context.json" ]; then
            echo -e "${YELLOW}No context file found. Creating test context...${NC}"

            echo "Choose scenario:"
            echo "  1) Solo (will use say)"
            echo "  2) 5-man party (will use party)"
            echo "  3) 10+ raid (will use raid)"
            read -p "Enter choice: " scenario

            case $scenario in
                1)
                    cat > wow_context.json << 'EOF'
{
  "zone": "Dornogal",
  "party": ["YourCharacter"],
  "class": "SHAMAN",
  "spec": "Enhancement"
}
EOF
                    echo "Created solo context"
                    ;;
                2)
                    cat > wow_context.json << 'EOF'
{
  "zone": "The Necrotic Wake",
  "party": ["Tank", "Healer", "DPS1", "DPS2", "YourCharacter"],
  "class": "SHAMAN",
  "spec": "Enhancement"
}
EOF
                    echo "Created 5-man party context"
                    ;;
                3)
                    cat > wow_context.json << 'EOF'
{
  "zone": "Icecrown Citadel",
  "party": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"],
  "class": "SHAMAN",
  "spec": "Enhancement"
}
EOF
                    echo "Created raid context"
                    ;;
            esac
        fi

        echo ""
        echo "Current context:"
        cat wow_context.json | python3 -c "import sys, json; ctx = json.load(sys.stdin); print(f\"  Party size: {len(ctx.get('party', []))}\")"
        echo ""

        echo "Recording with auto-detection..."
        echo "The channel will be chosen based on your party size"
        echo ""

        python wow_voice_chat.py --channel auto --context wow_context.json --mode once --duration 5
        ;;

    4)
        echo ""
        echo -e "${GREEN}Interactive Channel Demo${NC}"
        echo ""
        echo "This will run multiple tests in sequence."
        echo "Say the SAME message each time to see how it goes to different channels!"
        echo ""
        read -p "Press Enter to start..."

        for channel in say party raid guild; do
            echo ""
            echo "======================================"
            echo -e "${YELLOW}Testing: $channel chat${NC}"
            echo "======================================"
            echo "Recording 5 seconds... speak now!"
            echo ""

            python wow_voice_chat.py --channel "$channel" --mode once --duration 5

            echo ""
            read -p "Press Enter for next channel..."
        done

        echo ""
        echo "======================================"
        echo -e "${GREEN}Demo Complete!${NC}"
        echo "======================================"
        echo ""
        echo "You should have seen the same message go to different channels:"
        echo "  - say (/s)"
        echo "  - party (/p)"
        echo "  - raid (/raid)"
        echo "  - guild (/g)"
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "Next Steps"
echo "========================================="
echo ""
echo "For more information, see:"
echo "  - CHAT_CHANNELS.md (full documentation)"
echo ""
echo "Common usage patterns:"
echo ""
echo "1. Party chat by default:"
echo "   python wow_voice_chat.py --channel party --mode push-to-talk"
echo ""
echo "2. Auto-detect from context:"
echo "   python wow_voice_chat.py --channel auto --context wow_context.json --mode push-to-talk"
echo ""
echo "3. Use voice prefixes (most flexible):"
echo "   python wow_voice_chat.py --mode push-to-talk"
echo "   Then say: 'party lets go' or 'raid pull boss'"
echo ""
