#!/bin/bash

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

# Install required packages
echo "Installing necessary Python packages..."
apt-get update
apt-get install -y python3 python3-pip
pip3 install watchdog requests tenacity smtplib schedule

# Setup directory variables
SCRIPT_DIR="/path/to/your/script"  # Update with actual script directory
CONFIG_FILE="${SCRIPT_DIR}/config.json"
SERVICE_FILE="/etc/systemd/system/watcher.service"

# Create systemd service file
echo "Creating systemd service file..."
cat > ${SERVICE_FILE} << EOF
[Unit]
Description=Python Watcher Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/watcher.py ${CONFIG_FILE}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new service
echo "Reloading systemd manager configuration..."
systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling the watcher service..."
systemctl enable watcher.service

# Start the service
echo "Starting the watcher service..."
systemctl start watcher.service

# Output the status of the service
echo "Installation complete. Service status:"
systemctl status watcher.service
