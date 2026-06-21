# Feature Guide — Character + Scene Video Production

> **Branch:** `feature/bg-removal-compositing`
> This guide covers everything added beyond the base single-image workflow —
> automatic background removal, scene compositing, batch generation, and
> training a LoRA for consistent character identity across many videos.

---

## Table of Contents

1. [What Was Added](#1-what-was-added)
2. [How the Auto Compositing Works](#2-how-the-auto-compositing-works)
3. [Batch Video Generation](#3-batch-video-generation)
4. [Making Character Look Consistent — LoRA Training](#4-making-character-look-consistent--lora-training)
   - [Step 1 — Collect character images](#step-1--collect-character-images)
   - [Step 2 — Write captions](#step-2--write-captions)
   - [Step 3 — Train the LoRA](#step-3--train-the-lora)
   - [Step 4 — Use the LoRA in your workflow](#step-4--use-the-lora-in-your-workflow)
   - [Step 5 — Batch generate with the LoRA](#step-5--batch-generate-with-the-lora)
5. [Improving Video Quality](#5-improving-video-quality)
6. [Full Production Pipeline](#6-full-production-pipeline)
7. [File Reference](#7-file-reference)

---

## 1. What Was Added

| What | Where |
|------|-------|
| Auto background removal from character photo | `custom_nodes/rembg_node/__init__.py` |
| Character + scene composite workflow | `workflows/ltxv_096_gguf_scene_character.json` |
| Manual composite workflow (no auto BG removal) | `workflows/ltxv_096_gguf_i2v_dual_image.json` |
| Script to queue one video via API | `queue_test.py` |
| Script to queue many videos at once | `batch_generate.py` |

---

## 2. How the Auto Compositing Works

**Before this branch:** You had to manually cut out the character in an image editor and paste them onto a background before feeding the image to ComfyUI.

**Now:** Give it two images — the character photo and the background scene. The pipeline handles everything automatically.

```
character.jpg ──► [ RemoveBackgroundRembg ] ──► character (no background)
                            │                         │
                            └──── mask ───────────────┤
                                                      ▼
scene.png ────────────────────────────► [ ImageCompositeMasked ]
                                                      │
                                          [ LTXVImgToVideo ]
                                                      │
                                             [ KSampler ]
                                                      │
                                              [ VAEDecode ]
                                                      │
                                      [ CreateVideo ] ──► [ SaveVideo ]
```

### The RemoveBackgroundRembg Node

This is a custom node in `custom_nodes/rembg_node/` that wraps the `rembg` Python library.

| Setting | Options | Best for |
|---------|---------|---------|
| `u2net_human_seg` | Default | Photos of people — gives cleanest edges |
| `u2net` | General purpose | Animals, objects, anything non-human |
| `isnet-general-use` | High detail | Complex hair, fur, or fine edges |

On first use it downloads the model file (~176 MB) to `~/.u2net/`. Subsequent runs use the cached file — no re-download.

> **Why is it called `RemoveBackgroundRembg` and not `RemoveBackground`?**
> ComfyUI added its own built-in `RemoveBackground` node (commit `0d8b7510`).
> That built-in only outputs a MASK. Our node outputs IMAGE + MASK — both needed
> for compositing. Renaming avoids the clash.

---

## 3. Batch Video Generation

### The Problem

Running videos one by one through the ComfyUI browser UI doesn't scale. If you want 20 videos of the same character in different scenes with different actions, that's 20 manual clicks and 20 manual waits.

### The Solution — `batch_generate.py`

This script queues every combination of your scenes, prompts, and seeds in one command. ComfyUI processes them one at a time while you do something else.

```
3 scenes  ×  2 prompts  ×  3 seeds  =  18 videos queued automatically
```

### How to Use It

**Step 1** — Make sure ComfyUI is running:
```bash
cd <install-dir>
source venv/bin/activate
python main.py --listen
```

**Step 2** — Copy your images into ComfyUI's `input/` folder:
```
<install-dir>/input/
├── my_character.jpg
├── forest_bg.png
├── city_bg.png
└── beach_bg.png
```

**Step 3** — Edit the CONFIG section at the top of `batch_generate.py`:

```python
CHARACTER_IMAGE = "my_character.jpg"    # the character — same for all videos

SCENES = [
    "forest_bg.png",
    "city_bg.png",
    "beach_bg.png",
]

POSITIVE_PROMPTS = [
    "charname, laughing and jumping, warm sunlight, smooth natural motion, cinematic quality",
    "charname, waving hello enthusiastically, joyful expression, smooth motion, high detail",
]

SEEDS = [42, 123, 456]    # 3 different variations per scene+prompt

FRAMES = 249    # video length — see table below
```

**Step 4** — Run it:
```bash
python3 batch_generate.py
```

You'll see each job confirm as it queues:
```
Queueing 18 videos  (3 scenes × 2 prompts × 3 seeds)
Character: my_character.jpg  |  768×512  249 frames  8 steps

  [ 1/18] queued  scene=forest_bg.png   seed=42   id=a1b2c3...
  [ 2/18] queued  scene=forest_bg.png   seed=123  id=d4e5f6...
  ...
Done. 18/18 jobs queued.
```

Videos save to: `<install-dir>/output/video/ltxv_scene_character/`

### How Long Will It Take?

| Frames | Video length | Time per video (RTX 3060) | Use for |
|--------|-------------|--------------------------|---------|
| 97 | ~4 seconds | 5–8 min | Testing prompts quickly |
| 177 | ~7 seconds | 12–15 min | Short clips |
| 249 | ~10 seconds | 20–25 min | Final content |

> Frame count must always satisfy `8n + 1`. Use: 97, 177, 201, 225, 249.

At 249 frames, 18 videos ≈ **7–8 hours**. Queue it before you sleep, collect in the morning.

---

## 4. Making Character Look Consistent — LoRA Training

### The Problem

Every time you generate a video, the model re-reads the character image and reinterprets it slightly differently. Over 20+ videos you'll notice:
- Hair color or style shifts slightly
- Face shape changes between videos
- Outfit details inconsistent

For a content pipeline with one recurring character, this matters.

### The Solution — LoRA Fine-Tuning

A **LoRA** (Low-Rank Adaptation) is a small file you train on your character's images. After training:
- You add a trigger word to every prompt (e.g., `charname_style`)
- The model reproduces that exact character consistently across all videos
- Training is a one-time cost — reuse the LoRA forever after

---

### Step 1 — Collect Character Images

**Target: 30–50 images of your character.**

| Type | How many | What to look for |
|------|---------|-----------------|
| Full body, standing | 15–20 | Captures overall look, outfit, proportions |
| Face close-ups | 10–15 | Locks in face identity and expressions |
| Different angles | 5–10 | Side view, 3/4 view — helps 3D consistency |
| Different lighting | 5–10 | Makes the LoRA work in varied scene lighting |

**For animated characters** — pull stills directly from the source:
- Avoid frames with motion blur or compression artifacts
- Avoid frames where the character is partially cropped
- Background doesn't matter — it will be removed before training

**Image checklist before you start training:**
- [ ] All images are at least 512×512 pixels (768×768 preferred)
- [ ] Character is clearly visible, not blurry or cut off
- [ ] No watermarks, subtitles, or UI overlaid on the character
- [ ] All images have the same art style — don't mix styles
- [ ] Remove any image where the character looks "off model"

**Folder structure the trainer expects:**
```
lora_dataset/
└── images/
    └── 30_charname_style/
        ├── 001.png
        ├── 001.txt       ← caption for this image
        ├── 002.png
        ├── 002.txt
        └── ...
```

The folder name `30_charname_style` means:
- `30` → repeat these images 30 times per training epoch
- `charname_style` → the trigger phrase you'll type in prompts

---

### Step 2 — Write Captions

Every image needs a `.txt` caption file with the same name:

```
001.png  →  001.txt
002.png  →  002.txt
```

**Caption format — always start with your trigger word:**

```
charname_style, full body, red-haired anime girl in blue school uniform,
neutral standing pose, arms at sides, plain white background

charname_style, face closeup, smiling expression, bright blue eyes,
twin pigtails, soft warm lighting

charname_style, side view, walking pose, school bag on right shoulder,
looking straight ahead, outdoor park setting
```

**Caption rules:**
- Always lead with the trigger word (`charname_style`)
- Describe exactly what is in the image — don't guess or invent details
- Include: pose, expression, outfit, angle, background if relevant
- Do NOT describe motion — these are still images

**Auto-captioning option:** Florence2 is already installed in this setup. You can use it to generate base captions automatically, then prepend the trigger word to each `.txt` file.

---

### Step 3 — Train the LoRA

Full training setup is in [FINETUNE_GUIDE.md](FINETUNE_GUIDE.md).

Key settings specific to a character LoRA:

```toml
# Training config — character LoRA specific values

network_dim   = 32       # LoRA rank — 16 for simple characters, 32 for detailed
network_alpha = 16       # set to half of network_dim

learning_rate     = 1e-4
text_encoder_lr   = 5e-5

max_train_steps   = 800  # for animated characters, 600–1000 is enough
save_every_n_steps = 200  # saves checkpoints at 200, 400, 600, 800

resolution = 512,512     # use 768,768 if your GPU has room
```

**What to expect during training:**

| Step range | What you'll see |
|------------|----------------|
| 200–400 | Character starts appearing — rough but recognizable |
| 600–800 | Character is stable, details are consistent — usually the sweet spot |
| 1000+ | Risk of overtraining — character looks stiff or plasticky |

Test all four checkpoints (200, 400, 600, 800) and pick the one that looks most natural.

---

### Step 4 — Use the LoRA in Your Workflow

**Place the trained file here:**
```
<install-dir>/models/loras/charname_style.safetensors
```

**Add a LoRALoader node to your workflow:**

```
[ UnetLoaderGGUF ] ──► [ LoRALoader ] ──► model ──► LTXVImgToVideo
[ ClipLoaderGGUF ] ──► [ LoRALoader ] ──► clip  ──► CLIPTextEncode
```

In the `LoRALoader` node:
- Select your `charname_style.safetensors`
- Start with strength `0.8` for both model and clip
- Increase to `1.0` if the character isn't showing consistently

**Every prompt now includes the trigger word:**

```
charname_style, laughing and jumping in a sunny forest,
bright eyes sparkling, smooth natural motion, cinematic quality, high detail
```

---

### Step 5 — Batch Generate with the LoRA

With the LoRA trained and wired in, update `batch_generate.py` for production:

```python
POSITIVE_PROMPTS = [
    "charname_style, laughing and jumping, warm sunlight, smooth natural motion, cinematic quality",
    "charname_style, waving hello enthusiastically, joyful expression, high detail",
    "charname_style, dancing energetically, arms raised, fluid motion, vibrant colors",
    "charname_style, running and looking back, hair flowing, dynamic motion",
]

SCENES = [
    "forest_bg.png",
    "city_bg.png",
    "beach_bg.png",
    "mountain_bg.png",
    "indoor_bg.png",
]

SEEDS = [42, 123, 456]

# 5 scenes × 4 prompts × 3 seeds = 60 videos
# Queue before sleep → full content batch by morning
```

---

## 5. Improving Video Quality

### Fix Compositing Problems

| What you see | Why it happens | How to fix it |
|-------------|---------------|---------------|
| Character looks pasted on | Lighting direction mismatch | Choose scenes with lighting from the same side as the character photo |
| Edges of character are rough | rembg mask is imprecise | Switch to `isnet-general-use` in the `RemoveBackgroundRembg` node |
| Character is too big or too small | ImageScale size wrong | Adjust `width` / `height` in node 14 (ImageScale) |
| Character is in the wrong position | x/y offset wrong | Adjust `x` / `y` in node 15 (ImageCompositeMasked) |

### Write Better Motion Prompts

LTX-Video needs to know specifically what moves — not just how the character feels.

| Weak prompt | Strong prompt |
|------------|--------------|
| `"dynamic motion"` | `"arms swinging forward, hair flowing left to right"` |
| `"she is happy"` | `"laughing with mouth open, eyes crinkling, cheeks lifted"` |
| `"walking"` | `"taking long confident strides, shoulders swaying gently"` |
| `"dancing"` | `"spinning with arms raised, skirt fanning out, head tilting back"` |

### Seed Strategy

- Find a seed that gives good motion → that's your **base seed**
- For variations: `base`, `base + 1`, `base + 2` give related but distinct results
- For something completely different: jump by 1000+

### Post-Processing the Output

The raw video is 768×512. For final content quality:

1. **Upscale** — run through Real-ESRGAN or Topaz Video AI for 2× or 4× resolution
2. **Stabilize** — apply video stabilization if there's unwanted camera shake
3. **Color grade** — adjust contrast/saturation to better match character to scene

---

## 6. Full Production Pipeline

Once your LoRA is trained, this is the repeatable workflow for generating content at scale:

```
SETUP (one time only)
─────────────────────────────────────────────────────
1. Collect 30–50 character stills
2. Write captions for each image
3. Train LoRA — 600–800 steps
4. Test checkpoints, pick the best one
5. Add LoRALoader node to the scene_character workflow

PRODUCTION (repeat as many times as you want)
─────────────────────────────────────────────────────
6. Choose your background scenes (new PNGs in input/)
7. Write your action prompts (with trigger word)
8. Set seeds (2–3 per combination)
9. Run:  python3 batch_generate.py
10. Leave overnight — collect videos in the morning
11. Post-process the best outputs

Each new batch takes the same 3 steps: scenes + prompts + run.
```

### Time budget example

| Task | Time |
|------|------|
| Collect + prepare 40 character images | 1–2 hours |
| Write captions | 1 hour |
| Train LoRA (800 steps, RTX 3060) | ~2–3 hours |
| Test 4 prompts to validate LoRA | 30–60 min |
| **Total setup (one time)** | **~5–7 hours** |
| Queue and run 18 videos overnight | ~8 hours unattended |

---

## 7. File Reference

```
comfy_local_setup/
│
├── batch_generate.py                         Queue many videos at once
├── queue_test.py                             Queue one video via API
│
├── workflows/
│   ├── ltxv_096_gguf_scene_character.json   Auto BG removal + scene composite
│   ├── ltxv_096_gguf_i2v_dual_image.json    Manual composite (two images)
│   └── ltxv_096_gguf_i2v.json               Single image to video
│
├── custom_nodes/
│   └── rembg_node/
│       └── __init__.py                      RemoveBackgroundRembg node
│
├── FEATURES.md                              This file
├── FINETUNE_GUIDE.md                        Full LoRA training walkthrough
├── DUAL_IMAGE_GUIDE.md                      Manual composite workflow guide
└── USER_GUIDE.md                            Base workflow node-by-node guide
```
