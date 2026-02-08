#!/usr/bin/env python3
"""
Test to show the benefit of context in voice transcription
Demonstrates how context improves WoW-specific term recognition
"""

import json
from wow_voice_chat import WoWVoiceChat

def test_context_loading():
    """Test that context loads and generates proper prompts"""
    print("=" * 60)
    print("Testing WoW Context Loading")
    print("=" * 60)
    print()

    # Test 1: No context
    print("Test 1: Voice service WITHOUT context")
    print("-" * 60)
    service_no_context = WoWVoiceChat(context_file="nonexistent.json")
    loaded = service_no_context.load_context()

    if not loaded:
        print("✓ No context loaded (as expected)")
    else:
        print("✗ Unexpected context loaded")

    prompt, hotwords = service_no_context.build_prompt_from_context()
    print(f"\nInitial prompt (first 200 chars):")
    print(f"  {prompt[:200]}...")
    print(f"\nHotwords: {hotwords or 'None'}")
    print()

    # Test 2: With context
    print("Test 2: Voice service WITH context")
    print("-" * 60)

    # Try to load real context
    try:
        with open("wow_context.json") as f:
            context = json.load(f)
        print("✓ Found wow_context.json")
        print()
        print("Context data:")
        print(f"  Zone: {context.get('zone', 'N/A')}")
        print(f"  Subzone: {context.get('subzone', 'N/A')}")
        print(f"  Boss: {context.get('boss', 'N/A')}")
        print(f"  Target: {context.get('target', 'N/A')}")
        print(f"  Party: {', '.join(context.get('party', []))}")
        print(f"  Class: {context.get('class', 'N/A')}")
        print(f"  Spec: {context.get('spec', 'N/A')}")
        print()

        service_with_context = WoWVoiceChat(context_file="wow_context.json")
        service_with_context.load_context()
        prompt, hotwords = service_with_context.build_prompt_from_context()

        print(f"Initial prompt (first 300 chars):")
        print(f"  {prompt[:300]}...")
        print(f"\nHotwords: {hotwords or 'None'}")
        print()

        # Compare
        print("=" * 60)
        print("Comparison")
        print("=" * 60)
        print()
        print("WITHOUT context:")
        print(f"  Prompt length: {len(service_no_context.build_prompt_from_context()[0])} chars")
        print(f"  Hotwords: None")
        print()
        print("WITH context:")
        print(f"  Prompt length: {len(prompt)} chars")
        print(f"  Hotwords: {hotwords or 'None'}")
        print()

        # Check if context adds meaningful information
        has_zone = bool(context.get('zone'))
        has_boss = bool(context.get('boss'))
        has_party = bool(context.get('party'))

        if has_zone or has_boss or has_party:
            print("✓ Context contains meaningful data that will improve transcription")
            print()
            print("Expected improvements:")
            if has_zone:
                print(f"  - Better recognition of zone name: '{context['zone']}'")
            if has_boss:
                print(f"  - Better recognition of boss name: '{context['boss']}'")
            if has_party:
                print(f"  - Better recognition of party member names")
            print()
            print("Try saying these terms in voice tests to see the difference!")
        else:
            print("⚠ Context is mostly empty")
            print()
            print("To get meaningful context:")
            print("  1. Make sure WoW addon is installed and loaded")
            print("  2. Play WoW for a bit (change zones, target enemies)")
            print("  3. Run: python convert_wow_context.py")
            print("  4. Run this test again")

    except FileNotFoundError:
        print("✗ wow_context.json not found")
        print()
        print("To create it:")
        print("  1. Make sure WoW addon is installed")
        print("  2. Log in to WoW and play")
        print("  3. Run: python convert_wow_context.py")
        print("  4. Run this test again")
    except Exception as e:
        print(f"✗ Error loading context: {e}")

    print()
    print("=" * 60)
    print("Next Steps")
    print("=" * 60)
    print()
    print("To test actual voice transcription:")
    print("  1. Run: ./quick_test.sh")
    print("  2. Choose option 1 for quick test")
    print("  3. Say WoW-specific terms from your context")
    print()
    print("Compare transcription quality with/without context by:")
    print("  1. Recording the SAME phrase twice")
    print("  2. Once with --context wow_context.json")
    print("  3. Once without --context flag")
    print()


if __name__ == "__main__":
    test_context_loading()
