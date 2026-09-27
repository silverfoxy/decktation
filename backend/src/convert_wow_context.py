import os
import json
import re
import sys
from pathlib import Path


def extract_table(lua_content, table_name="DecktationContextDB"):
    """Extract table content taking nested braces into account."""
    m = re.search(rf'{table_name}\s*=\s*\{{', lua_content)
    if not m:
        return ""
    brace_start = m.end() - 1
    depth = 0
    for i in range(brace_start, len(lua_content)):
        if lua_content[i] == '{':
            depth += 1
        elif lua_content[i] == '}':
            depth -= 1
            if depth == 0:
                return lua_content[brace_start + 1:i]
    return ""


def parse_lua_table(lua_content):
    """
    Simple parser for WoW SavedVariables Lua format
    Handles basic table structure from DecktationContextDB
    """
    context = {}

    table_content = extract_table(lua_content, "DecktationContextDB")
    if not table_content:
        return context

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


def get_candidate_home_dirs():
    """Get candidate user home directories (works even if running as root under systemd)"""
    home_dirs = [Path.home()]
    if os.path.exists("/home"):
        try:
            for user_dir in Path("/home").iterdir():
                if user_dir.is_dir() and user_dir not in home_dirs and not user_dir.name.startswith("."):
                    home_dirs.append(user_dir)
        except Exception:
            pass
    return home_dirs


def find_savedvariables_file(wow_path=None):
    """
    Find the DecktationContext SavedVariables file.
    Searches common WoW installation locations and returns the most recently modified one.
    """
    candidate_files = []

    if wow_path:
        p = Path(wow_path)
        if p.is_file() and p.name == "DecktationContext.lua":
            return p
        if p.exists():
            for lua_path in p.glob("**/SavedVariables/DecktationContext.lua"):
                if lua_path.is_file():
                    candidate_files.append(lua_path)

    # Search common WoW paths across all discovered user homes
    home_dirs = get_candidate_home_dirs()

    relative_search_patterns = [
        "Games/battlenet/drive_c/Program Files (x86)/World of Warcraft",
        "Games/battlenet/drive_c/Program Files/World of Warcraft",
        "Games/world-of-warcraft/drive_c/Program Files (x86)/World of Warcraft",
        "Games/world-of-warcraft/drive_c/Program Files/World of Warcraft",
        ".steam/steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft",
        ".steam/steam/steamapps/compatdata/*/pfx/drive_c/Program Files/World of Warcraft",
        ".local/share/Steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft",
        ".local/share/Steam/steamapps/compatdata/*/pfx/drive_c/Program Files/World of Warcraft",
        ".var/app/com.valvesoftware.Steam/.steam/steam/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/World of Warcraft",
        ".local/share/bottles/bottles/*/drive_c/Program Files (x86)/World of Warcraft",
        ".local/share/bottles/bottles/*/drive_c/Program Files/World of Warcraft",
        ".local/share/lutris/runners/wine/*/drive_c/Program Files (x86)/World of Warcraft",
        ".wine/drive_c/Program Files (x86)/World of Warcraft",
        ".wine/drive_c/Program Files/World of Warcraft",
    ]

    for home in home_dirs:
        for rel_pattern in relative_search_patterns:
            try:
                for wow_dir in home.glob(rel_pattern):
                    if wow_dir.is_dir():
                        for lua_file in wow_dir.glob("**/SavedVariables/DecktationContext.lua"):
                            if lua_file.is_file():
                                candidate_files.append(lua_file)
            except Exception:
                continue

    if not candidate_files:
        return None

    try:
        candidate_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return candidate_files[0]
    except Exception:
        return candidate_files[0]


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
