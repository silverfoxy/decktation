#!/bin/bash
# Setup script for ydotoold service - run once with sudo
# Usage: sudo ./setup_ydotoold.sh

set -e

# Find ydotoold - check bundled first, then system locations
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check common plugin locations for bundled binary
PLUGIN_LOCATIONS=(
    "$SCRIPT_DIR/bin/ydotoold"
    "$HOME/homebrew/plugins/decktation/bin/ydotoold"
    "$HOME/.local/share/decky/plugins/decktation/bin/ydotoold"
)

YDOTOOLD_PATH=""
for path in "${PLUGIN_LOCATIONS[@]}" /usr/bin/ydotoold /usr/local/bin/ydotoold; do
    if [ -f "$path" ]; then
        YDOTOOLD_PATH="$path"
        break
    fi
done

if [ -z "$YDOTOOLD_PATH" ]; then
    echo "ydotoold not found in bundled or system locations."
    echo ""
    echo "Would you like to build ydotool from source now? (y/n)"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Building ydotool from source..."

        # Drop sudo privileges temporarily to build
        if [ -n "$SUDO_USER" ]; then
            # Run build script as the original user (not root)
            sudo -u "$SUDO_USER" bash "$SCRIPT_DIR/build_ydotool.sh"
        else
            bash "$SCRIPT_DIR/build_ydotool.sh"
        fi

        # Check again after build
        YDOTOOLD_PATH=""
        for path in "${PLUGIN_LOCATIONS[@]}" /usr/bin/ydotoold /usr/local/bin/ydotoold; do
            if [ -f "$path" ]; then
                YDOTOOLD_PATH="$path"
                break
            fi
        done

        if [ -z "$YDOTOOLD_PATH" ]; then
            echo "Error: Build completed but ydotoold still not found."
            exit 1
        fi
    else
        echo ""
        echo "Please install ydotool or run: ./build_ydotool.sh"
        echo "Then run this script again."
        exit 1
    fi
fi

echo "Found ydotoold at: $YDOTOOLD_PATH"

# Create systemd service with chmod after start
cat > /etc/systemd/system/ydotoold.service << EOF
[Unit]
Description=ydotool daemon for Decktation

[Service]
ExecStart=$YDOTOOLD_PATH
ExecStartPost=/bin/sleep 0.5
ExecStartPost=/bin/chmod 777 /tmp/.ydotool_socket

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service"

# Enable and start
systemctl daemon-reload
systemctl enable ydotoold
systemctl restart ydotoold

# Verify socket permissions
sleep 1
ls -la /tmp/.ydotool_socket

echo ""
echo "ydotoold service is now running with proper socket permissions"
echo "You can check status with: systemctl status ydotoold"
