#!/bin/bash

echo "Checking host configuration for Plan2Scene Web App..."

# 1. Check for NVIDIA Container Toolkit
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️  NVIDIA driver not found. Please install NVIDIA drivers."
else
    echo "✅ NVIDIA driver found."
fi

# Check for nvidia-container-cli (part of toolkit)
if ! command -v nvidia-container-cli &> /dev/null; then
    echo "❌ NVIDIA Container Toolkit not found."
    echo "To install on Ubuntu/Debian:"
    echo "  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
    echo "  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\"
    echo "    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\"
    echo "    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y nvidia-container-toolkit"
    echo "  sudo nvidia-ctk runtime configure --runtime=docker"
    echo "  sudo systemctl restart docker"
else
    echo "✅ NVIDIA Container Toolkit found."
fi

# 2. Check for Plan2Scene repo
PLAN2SCENE_DIR="../plan2scene"
if [ ! -d "$PLAN2SCENE_DIR" ]; then
    echo "⚠️  Plan2Scene repository not found at $PLAN2SCENE_DIR."
    echo "Cloning repository..."
    git clone https://github.com/3dlg-hcvc/plan2scene.git "$PLAN2SCENE_DIR"
    echo "✅ Plan2Scene cloned."
else
    echo "✅ Plan2Scene repository found."
fi

echo "Setup check complete."
