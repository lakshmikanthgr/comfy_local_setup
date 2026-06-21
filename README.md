# LTX-Video 0.9.6 GGUF — Image-to-Video on RTX 3060 12GB

A working ComfyUI setup for generating videos from images using the LTX-Video 0.9.6 2B model in GGUF format. Built specifically for consumer GPUs with 8–12GB VRAM. Includes three workflows: single image, manual dual-image composite, and automatic background removal + scene compositing.

---

## Branches

| Branch | What it adds |
|--------|-------------|
| `master` | Single image → video workflow only |
| `feature/bg-removal-compositing` | + automatic background removal and character-into-scene compositing |

> **This README covers the `feature/bg-removal-compositing` branch.**
> Clone this branch specifically:
> ```bash
> git clone -b feature/bg-removal-compositing \
>     https://github.com/lakshmikanthgr/comfy_local_setup.git
> ```

---

## Quick Start

### Option A — Native install (Linux only)

> **Requirements**: Linux, Python 3.10+, CUDA 12.1, GPU 10GB+ VRAM

```bash
git clone -b feature/bg-removal-compositing \
    https://github.com/lakshmikanthgr/comfy_local_setup.git
cd comfy_local_setup

# Installs ComfyUI, venv, all custom nodes, rembg, workflows, runs verification
bash install.sh

# Download 3 model files (installer prints exact paths)
# Then start:
cd comfyui-ltxv && source venv/bin/activate && python main.py --listen
```

Open: http://localhost:8188

### Option B — Docker (fully portable)

> **Requirements**: Docker, NVIDIA Container Toolkit, GPU 10GB+ VRAM

```bash
git clone -b feature/bg-removal-compositing \
    https://github.com/lakshmikanthgr/comfy_local_setup.git
cd comfy_local_setup

# Build all 4 images (10–20 min first run, cached after)
bash docker-build.sh

export MODELS_DIR=/path/to/your/models   # must contain unet/ clip/ vae/
docker compose up
```

Open: http://localhost:8188

---

## Models Required

Download all three from **huggingface.co/calcuis** and place them as shown:

| File | Folder |
|------|--------|
| `ltxv-2b-0.9.6-distilled-q6_k.gguf` | `models/unet/` |
| `t5xxl_fp32-q4_0.gguf` | `models/clip/` |
| `pig_video_enhanced_vae_fp32-f16.gguf` | `models/vae/` |

---

## Workflows

### Where the JSON files live

After `install.sh` runs, workflows are copied to ComfyUI's workflow browser directory:

```
<install-dir>/user/default/workflows/
├── ltxv_096_gguf_i2v.json                 ← single image → video
├── ltxv_096_gguf_i2v_dual_image.json      ← manual composite (two images)
└── ltxv_096_gguf_scene_character.json     ← auto BG removal + scene
```

The source files live in this repo at:

```
comfy_local_setup/workflows/
├── ltxv_096_gguf_i2v.json
├── ltxv_096_gguf_i2v_dual_image.json
└── ltxv_096_gguf_scene_character.json
```

They appear automatically in the ComfyUI workflow browser (top-right menu → "Browse Workflows"). You can also drag-and-drop a JSON file onto the ComfyUI canvas to load it.

---

### Workflow 1 — Single Image to Video (`ltxv_096_gguf_i2v`)

Animates one image into a ~10-second video.

**Pipeline:**
```
[UnetLoaderGGUF] ──────────────────────────────────────────► model
[ClipLoaderGGUF] ──────────────────────────────────────────► clip
[VaeGGUF] ─────────────────────────────────────────────────► vae
[LoadImage] ───────────────────────────────────────────────► image
[CLIPTextEncode] (positive) ──► [LTXVConditioning] ────────► conditioning
[CLIPTextEncode] (negative)  ──► [LTXVConditioning]
                                          │
                                 [LTXVImgToVideo] (768×512, 249 frames)
                                          │
                                    [KSampler] (8 steps, cfg=1.0)
                                          │
                                    [VAEDecode]
                                          │
                                  [CreateVideo] ──► [SaveVideo]
```

**How to use:**
1. Load the workflow in ComfyUI
2. Click the `LoadImage` node and upload your image
3. Edit the positive/negative prompt in the two `CLIPTextEncode` nodes
4. Click **Queue Prompt**
5. Output saved to `output/video/ltxv_i2v/`

---

### Workflow 2 — Dual Image Manual Composite (`ltxv_096_gguf_i2v_dual_image`)

Manually paste a character onto a scene background, then animate. You control the exact position and size.

**Extra nodes vs Workflow 1:**
```
[LoadImage] (character) ──► [ImageScale] ──────────────────► source
[LoadImage] (scene)     ──────────────────────────────────► destination
                                    │
                         [ImageCompositeMasked] ───────────► [LTXVImgToVideo]
```

**How to use:**
1. Upload your character image to the first `LoadImage` node
2. Upload your scene/background image to the second `LoadImage` node
3. Adjust `x`, `y` in `ImageCompositeMasked` to position the character
4. Adjust `width`/`height` in `ImageScale` to resize the character
5. Queue Prompt

---

### Workflow 3 — Auto Background Removal + Scene (`ltxv_096_gguf_scene_character`)

Automatically removes the background from the character image using rembg, then composites them onto the scene before generating the video. This is the recommended workflow for putting a person into a different background.

**Full pipeline:**
```
[LoadImage] (character) ──► [RemoveBackgroundRembg] ──► image (no bg)
                                       │                    │
                                       └──► mask            │
                                                            ▼
[LoadImage] (scene) ───────────────► [ImageCompositeMasked]
                                                │
                                       [LTXVImgToVideo] (768×512, 249 frames)
                                                │
                                          [KSampler]
                                                │
                                          [VAEDecode]
                                                │
                                        [CreateVideo] ──► [SaveVideo]
```

**How to use:**
1. Load `ltxv_096_gguf_scene_character` in ComfyUI
2. Click the first `LoadImage` node → upload your **character** photo (person, subject)
3. Click the second `LoadImage` node → upload your **scene/background** image
4. Edit positive/negative prompts
5. Queue Prompt — background removal runs automatically
6. Output saved to `output/video/ltxv_scene_character/`

**Node: RemoveBackgroundRembg**

This is a custom node in `custom_nodes/rembg_node/`. It wraps the `rembg` library.

| Parameter | Options | Default |
|-----------|---------|---------|
| `model` | `u2net_human_seg`, `u2net`, `isnet-general-use` | `u2net_human_seg` |

- Use `u2net_human_seg` for photos of people (best results)
- Use `u2net` for general objects
- Use `isnet-general-use` for complex scenes

On first run it downloads the model (~176MB to `~/.u2net/`). Subsequent runs use the cache.

**Outputs:** IMAGE (subject with transparent background) + MASK (alpha channel)

---

## Queuing Workflows via API (`queue_test.py`)

The repo includes `queue_test.py` — a script to submit the scene+character workflow to ComfyUI programmatically without opening the browser.

```bash
# Edit these two lines at the top of queue_test.py:
CHARACTER_IMAGE = "your_character.jpg"   # filename in ComfyUI's input/ folder
SCENE_IMAGE     = "your_scene.png"       # filename in ComfyUI's input/ folder

# Upload images first (ComfyUI must be running):
# Drop them into <install-dir>/input/  OR upload via the UI

# Then queue:
python3 queue_test.py
```

Output:
```json
{
  "prompt_id": "3fe9a6a9-...",
  "number": 0,
  "node_errors": {}
}
Queued! Prompt ID: 3fe9a6a9-...
Watch progress at: http://localhost:8189
```

The script reads the workflow JSON, builds the ComfyUI API prompt format, and POSTs to `/prompt`. It prints the inputs for key nodes so you can verify the wiring before it runs.

---

## Sampler Settings

These are fixed in all three workflows and should not be changed arbitrarily:

| Setting | Value | Why |
|---------|-------|-----|
| `steps` | 8 | Distilled model — more steps don't help |
| `cfg` | 1.0 | Guidance is baked in; higher values hurt quality |
| `sampler` | euler | Recommended for LTX-Video distilled |
| `scheduler` | sgm_uniform | Recommended for LTX-Video distilled |

## Frame Count and Duration

LTX-Video's temporal VAE requires frame count to satisfy `8n + 1`:

| Frames | Duration @ 25fps | VRAM fit on 3060 |
|--------|-----------------|-----------------|
| 97 | ~3.9 sec | Yes |
| 177 | ~7.1 sec | Yes |
| 201 | ~8.0 sec | Yes |
| 225 | ~9.0 sec | Yes |
| 249 | ~9.96 sec | Yes (tight) |

Default is 249. Reduce to 97 for fast iteration while testing prompts.

## Resolution

Width and height must be divisible by 32 (ideally 64).

| Use case | Resolution |
|----------|-----------|
| Portrait / passport photo | 512×768 |
| Landscape / scene | 768×512 |

---

## Generation Time (RTX 3060 12GB)

| Stage | Time |
|-------|------|
| Background removal (rembg) | ~10–30 sec |
| Model load (GGUF) | ~60 sec |
| KSampler (8 steps, 249 frames) | ~15–20 min |
| VAE decode | ~3–5 min |
| Video encode + save | ~30 sec |
| **Total** | **~20–30 min** |

Drop to 97 frames for ~5–8 min turnaround.

---

## Prompting Guide

Describe motion explicitly — LTX-Video responds to what moves, not just the scene.

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
- For close-up/passport photos: describe facial animation (laughing, blinking, head tilt)
- Avoid vague terms like "dynamic" — describe the actual movement
- Changing seed often produces more variation than tweaking the prompt

---

## Custom Node: RemoveBackgroundRembg

Source: `custom_nodes/rembg_node/__init__.py`

This node is registered as `RemoveBackgroundRembg` (not `RemoveBackground`) to avoid a name collision with the built-in ComfyUI background removal node added in ComfyUI commit `0d8b7510`. The built-in node outputs only a MASK and requires a separately loaded model — our node uses rembg directly and outputs both IMAGE and MASK.

| | Built-in (`RemoveBackground`) | Ours (`RemoveBackgroundRembg`) |
|--|--|--|
| Input | `bg_removal_model` + `image` | `image` + `model` name |
| Output | MASK only | IMAGE + MASK |
| Backend | ComfyUI bg_removal_model | rembg (ONNX) |
| Model download | manual (models/background_removal/) | automatic (~/.u2net/) |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ValueError: This gguf file is incompatible with llama.cpp` | Using city96 `CLIPLoaderGGUF` on a calcuis GGUF | Workflow uses calcuis `ClipLoaderGGUF` (lowercase l) — don't swap nodes |
| `AttributeError: vae has no attribute downscale_index_formula` | Using `LTXVImgToVideoConditionOnly` from the plugin | Workflow uses core `LTXVImgToVideo` instead |
| `CUDA out of memory` | Too many frames | Reduce `length` to 177 or 97 |
| `VaeGGUF` node not found | calcuis-gguf not loaded | Restart ComfyUI; check terminal for import errors |
| HTTP 400 `list index out of range` on node 15 | `RemoveBackground` name clash with built-in ComfyUI node | Rename to `RemoveBackgroundRembg` (already done in this repo) |
| Video output is static | Prompt doesn't describe motion | Add specific movement descriptors |
| rembg model downloading on first run | Normal — 176MB one-time download | Wait ~5 min, cached to `~/.u2net/` after |

---

## File Structure

```
comfy_local_setup/
├── install.sh                          # Full native setup script
├── docker-build.sh                     # Builds all 4 Docker images
├── docker-compose.yml                  # Wires images + model volume
├── queue_test.py                       # API script to queue scene+character workflow
│
├── workflows/                          # Source workflow JSONs (copied by install.sh)
│   ├── ltxv_096_gguf_i2v.json
│   ├── ltxv_096_gguf_i2v_dual_image.json
│   └── ltxv_096_gguf_scene_character.json
│
├── custom_nodes/
│   └── rembg_node/
│       └── __init__.py                 # RemoveBackgroundRembg node
│
├── docker/
│   ├── Dockerfile.base                 # CUDA 12.1 + Python 3.10
│   ├── Dockerfile.comfyui              # + ComfyUI + PyTorch
│   ├── Dockerfile.nodes                # + all custom nodes + rembg
│   └── Dockerfile.app                 # + workflows + entrypoint
│
└── docs/
    ├── USER_GUIDE.md
    ├── DUAL_IMAGE_GUIDE.md
    └── FINETUNE_GUIDE.md
```

---

## Why This Exists

The official [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) plugin ships example workflows targeting the **LTX-2 / LTX-2.3 series** — a 19B parameter model requiring 40GB+ VRAM. Those workflows use completely different nodes and will not work with the 2B GGUF model.

This setup uses **ltxv-2b-0.9.6** quantized to GGUF, runnable on a 12GB RTX 3060.

| | Official workflows | This setup |
|---|---|---|
| Model | LTX-2 / LTX-2.3 (19B safetensors) | ltxv-2b-0.9.6 (2B GGUF) |
| VRAM | 40GB+ | ~10–12GB |
| Text encoder | Gemma 3 12B | T5-XXL Q4_0 GGUF |
| UNet loader | CheckpointLoaderSimple | UnetLoaderGGUF (city96) |
| CLIP loader | native CLIPLoader | ClipLoaderGGUF (calcuis) |
| VAE loader | VAELoader (safetensors) | VaeGGUF (calcuis) |
| Sampler | LTXVBaseSampler (GUIDER-based) | KSampler (core ComfyUI) |
| I2V node | LTXVImgToVideoConditionOnly | LTXVImgToVideo (core ComfyUI) |

### Why two CLIP loaders exist

- **city96/ComfyUI-GGUF** (`CLIPLoaderGGUF`) — uses llama.cpp. Throws `ValueError: This gguf file is incompatible with llama.cpp!` on calcuis format files.
- **calcuis/gguf** (`ClipLoaderGGUF`, lowercase l) — uses `gguf_connector`. Handles the `t5xxl_fp32-q4_0.gguf` in this setup.

Both coexist without conflict because their registered node names differ.

### Why core LTXVImgToVideo instead of the plugin's node

`LTXVImgToVideoConditionOnly` accesses `vae.downscale_index_formula` — an attribute specific to the safetensors VAE object. A GGUF-loaded VAE from calcuis doesn't have it, causing `AttributeError` at runtime. The core node does the same job without accessing internal VAE attributes.

---

## Exact Versions

See [SETUP_SNAPSHOT.md](SETUP_SNAPSHOT.md) for all Python package versions and git commit hashes for every custom node.

**Hardware tested on:** RTX 3060 12GB, Ubuntu 22.04, CUDA 12.1, PyTorch 2.5.1
