#!/usr/bin/env python3
"""
Convert WoW SavedVariables to JSON context file
Parses DecktationContext.lua and outputs wow_context.json
"""

import json
import re
import sys
from pathlib import Path


def parse_lua_table(lua_content):
    """
    Simple parser for WoW SavedVariables Lua format
    Handles basic table structure from DecktationContextDB
    """
    context = {}

    # Extract the DecktationContextDB table
    match = re.search(r'DecktationContextDB\s*=\s*\{([^}]+)\}', lua_content, re.DOTALL)
    if not match:
        return context

    table_content = match.group(1)

    # Parse string fields
    string_fields = ['zone', 'subzone', 'boss', 'target', 'class', 'spec']
    for field in string_fields:
        pattern = rf'\["{field}"\]\s*=\s*"([^"]*)"'
        match = re.search(pattern, table_content)
        if match:
            context[field] = match.group(1)
        else:
            context[field] = ""

    # Parse party array
    party_match = re.search(r'\["party"\]\s*=\s*\{([^}]*)\}', table_content)
    if party_match:
        party_content = party_match.group(1)
        # Extract all quoted strings
        party_members = re.findall(r'"([^"]+)"', party_content)
        context['party'] = party_members
    else:
        context['party'] = []

    # Parse timestamp
    timestamp_match = re.search(r'\["timestamp"\]\s*=\s*(\d+)', table_content)
    if timestamp_match:
        context['timestamp'] = int(timestamp_match.group(1))

    return context


def find_savedvariables_file(wow_path=None):
    """
    Find the DecktationContext SavedVariables file
    Searches common WoW installation locations
    """
    # Common WoW paths on Steam Deck
    search_paths = []

    if wow_path:
        search_paths.append(Path(wow_path))

    # Steam Deck common locations
    search_paths.extend([
        Path.home() / ".steam/steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft",
        Path.home() / ".local/share/Steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft",
    ])

    # Look for SavedVariables
    for base_path in search_paths:
        if not base_path.exists():
            continue

        # Search in WTF directory for any account
        wtf_path = base_path / "WTF" / "Account"
        if wtf_path.exists():
            # Find any account directory
            for account_dir in wtf_path.iterdir():
                if account_dir.is_dir():
                    saved_vars = account_dir / "SavedVariables" / "DecktationContext.lua"
                    if saved_vars.exists():
                        return saved_vars

    return None


def convert_context(input_file, output_file="wow_context.json"):
    """
    Convert SavedVariables Lua file to JSON
    """
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: File not found: {input_file}")
        return False

    try:
        # Read Lua file
        with open(input_path, 'r', encoding='utf-8') as f:
            lua_content = f.read()

        # Parse to Python dict
        context = parse_lua_table(lua_content)

        if not context:
            print("Warning: Could not parse context from Lua file")
            context = {
                "zone": "",
                "subzone": "",
                "boss": "",
                "target": "",
                "party": [],
                "class": "",
                "spec": ""
            }

        # Write JSON
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2)

        print(f"Converted: {input_file} -> {output_file}")
        print(f"Context: {context['zone']} - {context['subzone']}")
        if context['boss']:
            print(f"Boss: {context['boss']}")
        if context['party']:
            print(f"Party: {', '.join(context['party'][:5])}")

        return True

    except Exception as e:
        print(f"Error converting context: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert WoW SavedVariables to JSON context")
    parser.add_argument("--input", "-i",
                       help="Path to DecktationContext.lua SavedVariables file")
    parser.add_argument("--output", "-o", default="wow_context.json",
                       help="Output JSON file (default: wow_context.json)")
    parser.add_argument("--wow-path",
                       help="Path to World of Warcraft installation (auto-detect if not specified)")
    parser.add_argument("--watch", action="store_true",
                       help="Watch for changes and auto-convert")

    args = parser.parse_args()

    input_file = args.input

    # Auto-detect SavedVariables file if not specified
    if not input_file:
        print("Searching for DecktationContext SavedVariables...")
        input_file = find_savedvariables_file(args.wow_path)

        if not input_file:
            print("Error: Could not find DecktationContext.lua")
            print("\nPlease specify the file manually with --input, or ensure:")
            print("  1. World of Warcraft is installed")
            print("  2. DecktationContext addon is installed and loaded in-game")
            print("  3. You've logged in at least once with the addon enabled")
            sys.exit(1)

        print(f"Found: {input_file}")

    # Convert once
    success = convert_context(input_file, args.output)

    if not success:
        sys.exit(1)

    # Watch mode
    if args.watch:
        import time

        print(f"\nWatching {input_file} for changes...")
        print("Press Ctrl+C to stop")

        last_mtime = Path(input_file).stat().st_mtime

        try:
            while True:
                current_mtime = Path(input_file).stat().st_mtime

                if current_mtime != last_mtime:
                    print(f"\n[{time.strftime('%H:%M:%S')}] File changed, converting...")
                    convert_context(input_file, args.output)
                    last_mtime = current_mtime

                time.sleep(2)  # Check every 2 seconds
        except KeyboardInterrupt:
            print("\nStopped watching")
