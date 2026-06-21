#!/usr/bin/env bash
# LTX-Video 0.9.6 GGUF — full setup script
# Branch: feature/bg-removal-compositing
# Tested on: Ubuntu 22.04, CUDA 12.1, RTX 3060 12GB
#
# Usage:
#   bash install.sh              → installs into ./comfyui-ltxv
#   bash install.sh /my/path     → installs into /my/path

set -euo pipefail

INSTALL_DIR="${1:-./comfyui-ltxv}"
COMFYUI_COMMIT="0d8b7510bdc5409f4a76c3191e122ddea50f4aa2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}==>${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC} $*"; }
error()   { echo -e "${RED}[error]${NC} $*"; exit 1; }
section() { echo ""; echo -e "${GREEN}── $* ──${NC}"; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
section "Pre-flight checks"

command -v git  >/dev/null 2>&1 || error "git not found. Install with: sudo apt install git"
command -v python3 >/dev/null 2>&1 || error "python3 not found."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION"
[[ "$PYTHON_VERSION" < "3.10" ]] && error "Python 3.10+ required (found $PYTHON_VERSION)"

if command -v nvidia-smi >/dev/null 2>&1; then
    GPU=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
    info "GPU: $GPU"
else
    warn "nvidia-smi not found — CUDA may not be available"
fi

# ── System packages ───────────────────────────────────────────────────────────
section "System packages"

MISSING_PKGS=()
command -v ffmpeg >/dev/null 2>&1       || MISSING_PKGS+=(ffmpeg)
python3 -c "import cv2" 2>/dev/null     || MISSING_PKGS+=(python3-opencv)
ldconfig -p | grep -q libGL             || MISSING_PKGS+=(libgl1-mesa-glx)
ldconfig -p | grep -q libglib-2         || MISSING_PKGS+=(libglib2.0-0)

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    info "Installing system packages: ${MISSING_PKGS[*]}"
    if command -v sudo >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq "${MISSING_PKGS[@]}"
    else
        error "Missing system packages: ${MISSING_PKGS[*]}\nInstall manually: apt-get install ${MISSING_PKGS[*]}"
    fi
else
    info "System packages OK"
fi

# ── ComfyUI core ──────────────────────────────────────────────────────────────
section "ComfyUI core"

info "Installing into: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ -f "main.py" ]; then
    warn "ComfyUI already present — skipping clone"
else
    git clone https://github.com/comfyanonymous/ComfyUI.git .
    git checkout "$COMFYUI_COMMIT"
    info "ComfyUI at $COMFYUI_COMMIT"
fi

# ── Python environment ────────────────────────────────────────────────────────
section "Python virtual environment"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    info "Created venv"
else
    info "venv already exists — reusing"
fi

source venv/bin/activate
pip install --upgrade pip --quiet

# ── PyTorch ───────────────────────────────────────────────────────────────────
section "PyTorch (CUDA 12.1)"

if python -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    info "PyTorch with CUDA already installed — skipping"
else
    pip install --quiet \
        torch==2.5.1+cu121 \
        torchvision==0.20.1+cu121 \
        torchaudio==2.5.1+cu121 \
        --index-url https://download.pytorch.org/whl/cu121
    info "PyTorch 2.5.1+cu121 installed"
fi

# ── ComfyUI requirements ──────────────────────────────────────────────────────
section "ComfyUI base requirements"
pip install --quiet -r requirements.txt
info "ComfyUI requirements installed"

# ── Extra packages ────────────────────────────────────────────────────────────
section "Extra packages"
pip install --quiet \
    accelerate==1.13.0 \
    diffusers==0.38.0 \
    gguf==0.18.0 \
    gguf-connector==3.5.4 \
    numpy==2.2.6 \
    "safetensors==0.8.0rc0" \
    torchsde==0.2.6 \
    "transformers==5.7.0" \
    "rembg[gpu]==2.0.59"
info "Extra packages installed"

# ── Custom nodes ──────────────────────────────────────────────────────────────
section "Custom nodes"
cd custom_nodes

clone_node() {
    local name=$1 url=$2 commit=$3
    if [ -d "$name" ]; then
        info "$name already present — skipping"
    else
        echo "  -> $name"
        git clone --quiet "$url" "$name"
        git -C "$name" checkout --quiet "$commit"
    fi
    if [ -f "$name/requirements.txt" ]; then
        pip install --quiet -r "$name/requirements.txt"
    fi
}

clone_node "ComfyUI-GGUF"            "https://github.com/city96/ComfyUI-GGUF.git"                "6ea2651e7df66d7585f6ffee804b20e92fb38b8a"
clone_node "calcuis-gguf"            "https://github.com/calcuis/gguf.git"                        "2902c546c18231e4323fa2c0d63455c34ed79e5a"
clone_node "ComfyUI-LTXVideo"        "https://github.com/Lightricks/ComfyUI-LTXVideo.git"         "4f45fd6c222eb06eb3e46605da62e7c889e4be5c"
clone_node "ComfyUI-Manager"         "https://github.com/ltdrdata/ComfyUI-Manager.git"            "8d5c12037f873c2f9e059e4f9c409a2835a9b8cf"
clone_node "ComfyUI-VideoHelperSuite" "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite"   "2984ec4c4b93292421888f38db74a5e8802a8ff8"
clone_node "ComfyUI-WanVideoWrapper" "https://github.com/Kijai/ComfyUI-WanVideoWrapper.git"       "df8f3e49daaad117cf3090cc916c83f3d001494c"
clone_node "ComfyUI-Florence2"       "https://github.com/kijai/ComfyUI-Florence2.git"             "9ece3de914214c5f581d725167bc9d0eeb0d1120"

# Our custom background removal node
if [ -d "rembg_node" ]; then
    info "rembg_node already present — skipping"
else
    cp -r "$SCRIPT_DIR/custom_nodes/rembg_node" .
    info "rembg_node installed"
fi

cd ..

# ── Workflows ─────────────────────────────────────────────────────────────────
section "Workflows"
mkdir -p user/default/workflows
cp "$SCRIPT_DIR/workflows/"*.json user/default/workflows/
info "Workflows copied: $(ls user/default/workflows/*.json | wc -l) files"

# ── Model directories ─────────────────────────────────────────────────────────
section "Model directories"
mkdir -p models/unet models/clip models/vae models/checkpoints models/loras
info "Model directories created"

# ── Verify ────────────────────────────────────────────────────────────────────
section "Verification"

ERRORS=0

python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" \
    && info "PyTorch CUDA: OK" \
    || { warn "PyTorch CUDA: FAILED — check CUDA driver"; ERRORS=$((ERRORS+1)); }

python -c "import rembg" \
    && info "rembg: OK" \
    || { warn "rembg: import failed"; ERRORS=$((ERRORS+1)); }

python -c "from gguf_connector.reader import GGUFReader" \
    && info "gguf_connector: OK" \
    || { warn "gguf_connector: import failed"; ERRORS=$((ERRORS+1)); }

[ -f "custom_nodes/rembg_node/__init__.py" ] \
    && info "rembg_node: OK" \
    || { warn "rembg_node: missing"; ERRORS=$((ERRORS+1)); }

WORKFLOW_COUNT=$(ls user/default/workflows/*.json 2>/dev/null | wc -l)
[ "$WORKFLOW_COUNT" -ge 3 ] \
    && info "Workflows: $WORKFLOW_COUNT files OK" \
    || { warn "Workflows: only $WORKFLOW_COUNT files found"; ERRORS=$((ERRORS+1)); }

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"

if [ "$ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}  Setup complete with $ERRORS warning(s). Review output above.${NC}"
else
    echo -e "${GREEN}  Setup complete. All checks passed.${NC}"
fi

echo ""
echo "  NEXT — Download 3 model files into:"
echo ""
echo "    $INSTALL_DIR/models/unet/  ← ltxv-2b-0.9.6-distilled-q6_k.gguf"
echo "    $INSTALL_DIR/models/clip/  ← t5xxl_fp32-q4_0.gguf"
echo "    $INSTALL_DIR/models/vae/   ← pig_video_enhanced_vae_fp32-f16.gguf"
echo ""
echo "  All three: huggingface.co/calcuis"
echo ""
echo "  THEN — Start ComfyUI:"
echo "    cd $INSTALL_DIR"
echo "    source venv/bin/activate"
echo "    python main.py --listen"
echo ""
echo "  Open: http://localhost:8188"
echo ""
echo "  Workflows ready in the browser:"
echo "    ltxv_096_gguf_i2v               (single image → video)"
echo "    ltxv_096_gguf_i2v_dual_image    (manual composite)"
echo "    ltxv_096_gguf_scene_character   (auto BG removal + scene)"
echo "============================================================"
