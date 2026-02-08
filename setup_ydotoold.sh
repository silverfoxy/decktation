#!/bin/bash
# Setup script for ydotoold service - run once with sudo
# Usage: sudo ./setup_ydotoold.sh

set -e

# Find ydotoold
YDOTOOLD_PATH=""
for path in /home/deck/.nix-profile/bin/ydotoold /usr/bin/ydotoold /usr/local/bin/ydotoold; do
    if [ -f "$path" ]; then
        YDOTOOLD_PATH="$path"
        break
    fi
done

if [ -z "$YDOTOOLD_PATH" ]; then
    echo "Error: ydotoold not found. Please install ydotool first."
    exit 1
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
