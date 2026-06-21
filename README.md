# LTX-Video 0.9.6 GGUF — Image-to-Video on RTX 3060 12GB

A working ComfyUI workflow for generating 10-second videos from a single image using the LTX-Video 0.9.6 2B model in GGUF format. Built specifically for consumer GPUs with 8–12GB VRAM.

---

## Quick Start

### Option A — Docker (recommended, fully portable)

> **Requirements**: Docker, [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html), GPU 10GB+ VRAM

```bash
# 1. Clone this repo
git clone https://github.com/lakshmikanthgr/comfy_local_setup.git
cd comfy_local_setup

# 2. Build all 4 images (takes 10–20 min on first run, cached after)
bash docker-build.sh

# 3. Download the 3 model files (see Models section below)
#    and point MODELS_DIR at the folder containing unet/ clip/ vae/

# 4. Start
export MODELS_DIR=/path/to/your/models
docker compose up

# Open http://localhost:8188
```

The workflow `ltxv_096_gguf_i2v` appears in the workflow browser automatically.

### Option B — Native install (Linux only)

> **Requirements**: Linux, Python 3.10+, CUDA 12.1, GPU 10GB+ VRAM

```bash
git clone https://github.com/lakshmikanthgr/comfy_local_setup.git
cd comfy_local_setup
bash install.sh
# Download models, then:
cd comfyui-ltxv && source venv/bin/activate && python main.py --listen
```

---

## Documentation

| File | Contents |
|------|----------|
| [USER_GUIDE.md](USER_GUIDE.md) | How to use the workflow — every node, every parameter, plain English |
| [DUAL_IMAGE_GUIDE.md](DUAL_IMAGE_GUIDE.md) | Character + scene compositing — animate a person inside a background |
| [FINETUNE_GUIDE.md](FINETUNE_GUIDE.md) | How to fine-tune the model on your own images and videos |
| [SETUP_SNAPSHOT.md](SETUP_SNAPSHOT.md) | Exact versions of every component |

---

## Why This Exists

The official [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) plugin ships example workflows, but they target the **LTX-2 / LTX-2.3 series** — a 19B parameter model that requires 40GB+ VRAM. Those workflows use completely different nodes, encoders (Gemma 3 12B), and model formats. They will not work with the older 2B GGUF model.

This setup uses the **ltxv-2b-0.9.6** family — the original smaller LTX-Video model — quantized to GGUF format so it runs on a 12GB RTX 3060.

---

## How This Differs from the Official Workflow

| | Official ComfyUI-LTXVideo (example workflows) | This Setup |
|---|---|---|
| **Model** | LTX-2 / LTX-2.3 (19B safetensors) | ltxv-2b-0.9.6 (2B GGUF) |
| **VRAM needed** | 40GB+ | ~10–12GB |
| **Text encoder** | Gemma 3 12B | T5-XXL (Q4_0 GGUF) |
| **UNet loader** | CheckpointLoaderSimple | UnetLoaderGGUF (city96) |
| **CLIP loader** | native CLIPLoader | ClipLoaderGGUF (calcuis) |
| **VAE loader** | VAELoader (safetensors) | VaeGGUF (calcuis) |
| **Sampler node** | LTXVBaseSampler (custom, GUIDER-based) | KSampler (core ComfyUI) |
| **I2V node** | LTXVImgToVideoConditionOnly | LTXVImgToVideo (core ComfyUI) |

### The critical problem: two incompatible CLIP loaders

There are two separate GGUF ecosystems for ComfyUI:

- **city96/ComfyUI-GGUF** — uses llama.cpp under the hood. Its `CLIPLoaderGGUF` only works with llama.cpp-compatible GGUF files.
- **calcuis/gguf** — uses its own `gguf_connector` reader. Its `ClipLoaderGGUF` (lowercase `l`) handles a different GGUF format used by the calcuis model releases.

The `t5xxl_fp32-q4_0.gguf` file in this setup is in calcuis format. Using city96's `CLIPLoaderGGUF` on it throws:

```
ValueError: This gguf file is incompatible with llama.cpp!
```

**Fix**: use calcuis's `ClipLoaderGGUF` node instead. Both nodes coexist without conflict because their registered names differ (`CLIPLoaderGGUF` vs `ClipLoaderGGUF`).

### Why LTXVImgToVideo (core) instead of LTXVImgToVideoConditionOnly (custom)

The ComfyUI-LTXVideo plugin's `LTXVImgToVideoConditionOnly` node accesses `vae.downscale_index_formula` — an attribute specific to the safetensors LTX-Video VAE object. A GGUF-loaded VAE from calcuis doesn't have this attribute, causing an `AttributeError` at runtime.

The core ComfyUI `LTXVImgToVideo` node (in `comfy_extras/nodes_lt.py`) does the same thing — encodes the image, creates an empty latent, and applies the image mask — but without accessing any VAE-specific internal attributes. It's simpler and GGUF-safe.

---

## Setup

### 1. Clone ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install custom nodes

```bash
cd custom_nodes

# GGUF UNet loader (city96) — for the main model
git clone https://github.com/city96/ComfyUI-GGUF.git
cd ComfyUI-GGUF && git checkout 6ea2651e7df66d7585f6ffee804b20e92fb38b8a && cd ..

# calcuis GGUF toolkit — for CLIP and VAE GGUF loading
git clone https://github.com/calcuis/gguf.git calcuis-gguf
cd calcuis-gguf && git checkout 2902c546c18231e4323fa2c0d63455c34ed79e5a && cd ..

# LTXVideo plugin — provides LTXVImgToVideo and LTXVConditioning nodes
git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
cd ComfyUI-LTXVideo && git checkout 4f45fd6c222eb06eb3e46605da62e7c889e4be5c && cd ..

cd ..
```

Install Python dependencies:

```bash
pip install gguf-connector
```

### 3. Download models

| File | Place in |
|------|----------|
| `ltxv-2b-0.9.6-distilled-q6_k.gguf` | `models/unet/` |
| `t5xxl_fp32-q4_0.gguf` | `models/clip/` |
| `pig_video_enhanced_vae_fp32-f16.gguf` | `models/vae/` |

All three are available from the calcuis releases on Hugging Face.

### 4. Load the workflow

Copy `user/default/workflows/ltxv_096_gguf_i2v.json` into your ComfyUI `user/default/workflows/` folder. It will appear in the workflow browser automatically.

---

## Workflow Overview

```
[UnetLoaderGGUF]          loads ltxv-2b-0.9.6-distilled-q6_k.gguf
[ClipLoaderGGUF]          loads t5xxl_fp32-q4_0.gguf, type=ltxv
[VaeGGUF]                 loads pig_video_enhanced_vae_fp32-f16.gguf
[LoadImage]               your input image
       |
[CLIPTextEncode] x2 ──► [LTXVConditioning]   injects frame_rate=25
                                  |
                         [LTXVImgToVideo]     768×512, 249 frames (~10 sec), strength=1.0
                                  |
                          [KSampler]          steps=8, cfg=1.0, euler, sgm_uniform
                                  |
                          [VAEDecode]
                                  |
                         [CreateVideo] ──► [SaveVideo]
                                           output/video/ltxv_i2v/
```

### Sampler settings explained

The `ltxv-2b-0.9.6-distilled` model is a **distilled** model. Distillation compresses many denoising steps into fewer, so:

- `steps=8` is sufficient (6–12 works, more does not help)
- `cfg=1.0` — classifier-free guidance scale at 1.0 means guidance is effectively off; distilled models bake guidance in
- `euler` + `sgm_uniform` — the recommended scheduler for LTX-Video distilled variants

Using higher CFG or more steps with a distilled model produces worse results, not better.

### Frame count constraint

LTX-Video's temporal VAE compresses time by a factor of 8. The frame count must satisfy:

```
length = 8n + 1   (e.g. 9, 17, 25, 33, ..., 97, 177, 201, 225, 249)
```

At 25fps:

| Frames | Duration |
|--------|----------|
| 97     | ~3.9 sec |
| 177    | ~7.1 sec |
| 201    | ~8.0 sec |
| 225    | ~9.0 sec |
| 249    | ~9.96 sec |

### Resolution constraint

Width and height must both be divisible by 32 (ideally 64). For portrait/passport images use 512×768. For landscape use 768×512.

---

## Prompting Guide

LTX-Video 0.9.6 responds well to explicit motion descriptions. Describe what moves, not just what the scene looks like.

**Positive prompt structure:**
```
[subject] [specific motion], [lighting], smooth natural motion, cinematic quality, high detail
```

**Example (portrait/face):**
```
A cheerful 3 year old girl laughing with pure joy, bright eyes sparkling, wide natural smile,
rosy chubby cheeks lifting, head tilting side to side playfully, small shoulders bouncing with
giggles, soft warm golden lighting on face, smooth natural child movement, lifelike facial
animation, cinematic portrait, high detail, vibrant colors
```

**Negative prompt:**
```
worst quality, low quality, blurry, jittery, flickering, distorted face, deformed features,
unnatural motion, inconsistent motion, choppy, artifacts, overexposed, dark, dull colors,
static, frozen, lifeless expression, morphing face, multiple faces
```

**Tips:**
- For close-up/passport photos: focus on facial animation (laughing, blinking, head tilt) — body movement can't be generated from what isn't in frame
- Avoid vague terms like "dynamic" or "motion" — describe the actual movement explicitly
- Changing the seed often produces more variation than tweaking the prompt

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ValueError: This gguf file is incompatible with llama.cpp` | Using city96's `CLIPLoaderGGUF` on a calcuis GGUF file | Switch to calcuis's `ClipLoaderGGUF` node |
| `AttributeError: vae has no attribute downscale_index_formula` | Using `LTXVImgToVideoConditionOnly` from the plugin | Use core `LTXVImgToVideo` instead |
| `CUDA out of memory` | Too many frames for 12GB VRAM | Reduce length: try 177 or 201 frames |
| VAE node not found / `VaeGGUF` missing | calcuis-gguf not loaded | Restart ComfyUI; check terminal for import errors |
| Video output is static / no motion | Prompt doesn't describe motion explicitly | Add specific movement descriptors to positive prompt |

---

## Exact Versions (Frozen)

See [SETUP_SNAPSHOT.md](SETUP_SNAPSHOT.md) for the full version table including all Python package versions and git commit hashes for every custom node.

---

## Hardware

Tested on: RTX 3060 12GB, Ubuntu 22.04, CUDA 12.1, PyTorch 2.5.1
