#!/usr/bin/env bash
# LTX-Video 0.9.6 GGUF — ComfyUI setup script
# Reproduces the exact environment for image-to-video on RTX 3060 12GB
# Usage: bash install.sh [install_dir]
# Default install_dir: ./comfyui-ltxv

set -e

INSTALL_DIR="${1:-./comfyui-ltxv}"
COMFYUI_COMMIT="0d8b7510bdc5409f4a76c3191e122ddea50f4aa2"

echo "==> Installing into: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# ── 1. ComfyUI core ──────────────────────────────────────────────────────────
echo ""
echo "==> Cloning ComfyUI..."
git clone https://github.com/comfyanonymous/ComfyUI.git .
git checkout "$COMFYUI_COMMIT"

# ── 2. Python environment ─────────────────────────────────────────────────────
echo ""
echo "==> Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "==> Installing PyTorch (CUDA 12.1)..."
pip install --quiet \
    torch==2.5.1+cu121 \
    torchvision==0.20.1+cu121 \
    torchaudio==2.5.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

echo ""
echo "==> Installing ComfyUI requirements..."
pip install --quiet -r requirements.txt

echo ""
echo "==> Installing extra packages..."
pip install --quiet \
    accelerate==1.13.0 \
    diffusers==0.38.0 \
    gguf==0.18.0 \
    gguf-connector==3.5.4 \
    numpy==2.2.6 \
    "safetensors==0.8.0rc0" \
    torchsde==0.2.6 \
    "transformers==5.7.0"

# ── 3. Custom nodes ───────────────────────────────────────────────────────────
echo ""
echo "==> Installing custom nodes..."
cd custom_nodes

echo "  -> ComfyUI-GGUF (city96)"
git clone https://github.com/city96/ComfyUI-GGUF.git
git -C ComfyUI-GGUF checkout 6ea2651e7df66d7585f6ffee804b20e92fb38b8a

echo "  -> calcuis-gguf"
git clone https://github.com/calcuis/gguf.git calcuis-gguf
git -C calcuis-gguf checkout 2902c546c18231e4323fa2c0d63455c34ed79e5a

echo "  -> ComfyUI-LTXVideo (Lightricks)"
git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
git -C ComfyUI-LTXVideo checkout 4f45fd6c222eb06eb3e46605da62e7c889e4be5c

echo "  -> ComfyUI-Manager"
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
git -C ComfyUI-Manager checkout 8d5c12037f873c2f9e059e4f9c409a2835a9b8cf

echo "  -> ComfyUI-VideoHelperSuite"
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
git -C ComfyUI-VideoHelperSuite checkout 2984ec4c4b93292421888f38db74a5e8802a8ff8

echo "  -> ComfyUI-WanVideoWrapper"
git clone https://github.com/Kijai/ComfyUI-WanVideoWrapper.git
git -C ComfyUI-WanVideoWrapper checkout df8f3e49daaad117cf3090cc916c83f3d001494c

echo "  -> ComfyUI-Florence2"
git clone https://github.com/kijai/ComfyUI-Florence2.git
git -C ComfyUI-Florence2 checkout 9ece3de914214c5f581d725167bc9d0eeb0d1120

cd ..

# ── 4. Workflow ───────────────────────────────────────────────────────────────
echo ""
echo "==> Copying workflow..."
mkdir -p user/default/workflows
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/workflows/ltxv_096_gguf_i2v.json" user/default/workflows/

# ── 5. Model directory structure ──────────────────────────────────────────────
echo ""
echo "==> Creating model directories..."
mkdir -p models/unet models/clip models/vae

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Setup complete."
echo "============================================================"
echo ""
echo "NEXT STEP — Download these 3 model files manually:"
echo ""
echo "  models/unet/  <-- ltxv-2b-0.9.6-distilled-q6_k.gguf"
echo "  models/clip/  <-- t5xxl_fp32-q4_0.gguf"
echo "  models/vae/   <-- pig_video_enhanced_vae_fp32-f16.gguf"
echo ""
echo "All three are from the calcuis releases on Hugging Face."
echo "Search: huggingface.co/calcuis"
echo ""
echo "To start ComfyUI:"
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo "  python main.py --listen"
echo ""
echo "The workflow 'ltxv_096_gguf_i2v' will appear in the workflow browser."
echo "============================================================"
