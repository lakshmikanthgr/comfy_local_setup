#!/usr/bin/env bash
# Builds all 4 images in order. Each layer caches independently.
# Usage: bash docker-build.sh
# Re-run after any Dockerfile change — only changed layers rebuild.
#
# Includes: background removal node (rembg_node), all 3 workflows,
# all custom nodes pinned to exact commits.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/4] Building base image (CUDA + Python)..."
docker build -f "$SCRIPT_DIR/docker/Dockerfile.base" \
    -t comfyui-base:latest \
    "$SCRIPT_DIR"

echo ""
echo "==> [2/4] Building ComfyUI core image..."
docker build -f "$SCRIPT_DIR/docker/Dockerfile.comfyui" \
    -t comfyui-core:latest \
    "$SCRIPT_DIR"

echo ""
echo "==> [3/4] Building custom nodes image..."
docker build -f "$SCRIPT_DIR/docker/Dockerfile.nodes" \
    -t comfyui-nodes:latest \
    "$SCRIPT_DIR"

echo ""
echo "==> [4/4] Building app image (workflow + entrypoint)..."
docker build -f "$SCRIPT_DIR/docker/Dockerfile.app" \
    -t comfyui-ltxv-app:latest \
    "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  All images built successfully."
echo ""
echo "  comfyui-base:latest       CUDA 12.1 + Python 3.10"
echo "  comfyui-core:latest       + ComfyUI + PyTorch + pip deps"
echo "  comfyui-nodes:latest      + all custom nodes"
echo "  comfyui-ltxv-app:latest   + workflow (ready to run)"
echo ""
echo "  Next: set your models directory and start"
echo "    export MODELS_DIR=/path/to/your/models"
echo "    docker compose up"
echo "============================================================"
