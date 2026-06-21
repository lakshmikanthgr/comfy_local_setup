# Feature Guide — Character + Scene Video Production

This guide covers everything on the `feature/bg-removal-compositing` branch beyond the basic single-image workflow: what was added, how to use it, and how to scale up to producing many videos of a consistent character across different scenes.

---

## What Was Added in This Branch

| Feature | Files |
|---------|-------|
| Automatic background removal from character image | `custom_nodes/rembg_node/__init__.py` |
| Scene + character composite workflow | `workflows/ltxv_096_gguf_scene_character.json` |
| Manual composite workflow | `workflows/ltxv_096_gguf_i2v_dual_image.json` |
| API queuing script (single job) | `queue_test.py` |
| Batch generation script (multiple jobs) | `batch_generate.py` |

---

## The Problem This Solves

The base workflow takes one image and animates it. If you want a specific character placed inside a different scene or background, you previously had to composite them manually in an image editor before feeding the image to ComfyUI.

This branch automates that:

```
character.jpg  ──► [RemoveBackgroundRembg] ──► character (no bg) + mask
scene.png      ──────────────────────────────► scene image
                                    │
                         [ImageCompositeMasked]
                                    │
                         [LTXVImgToVideo] → [KSampler] → video
```

The `RemoveBackgroundRembg` node uses the `rembg` library with the `u2net_human_seg` ONNX model — optimized for human subjects. It downloads automatically on first use (~176MB to `~/.u2net/`).

> **Note on node name:** The node is registered as `RemoveBackgroundRembg`, not `RemoveBackground`. ComfyUI commit `0d8b7510` added its own built-in `RemoveBackground` node that only outputs a MASK. Ours outputs IMAGE + MASK. The name avoids the collision.

---

## Batch Video Generation (`batch_generate.py`)

### What it does

Queues multiple videos in one command by iterating over every combination of:
- Scenes (background images)
- Prompts (what the character is doing)
- Seeds (variation per prompt)

Example: 3 scenes × 2 prompts × 3 seeds = **18 videos queued automatically**.

### Setup

1. Make sure ComfyUI is running: `python main.py --listen`
2. Upload all your scene images and the character image into ComfyUI's `input/` folder
3. Open `batch_generate.py` and edit the CONFIG section at the top:

```python
CHARACTER_IMAGE = "my_character.jpg"   # one character, used for all videos

SCENES = [
    "forest_bg.png",
    "city_bg.png",
    "beach_bg.png",
]

POSITIVE_PROMPTS = [
    "charname, laughing and jumping, warm sunlight, smooth natural motion, cinematic quality",
    "charname, waving hello enthusiastically, joyful expression, smooth motion, high detail",
]

SEEDS = [42, 123, 456]   # 3 variations per scene+prompt combination

FRAMES = 249   # 249 = ~10 sec  |  97 = ~4 sec (faster for testing)
```

4. Run:

```bash
python3 batch_generate.py
```

Output:
```
Queueing 18 videos  (3 scenes × 2 prompts × 3 seeds)
Character: my_character.jpg  |  768×512  249 frames  8 steps

  [ 1/18] queued  scene=forest_bg.png  seed=42   id=a1b2c3...
  [ 2/18] queued  scene=forest_bg.png  seed=123  id=d4e5f6...
  ...

Done. 18/18 jobs queued.
Watch: http://localhost:8189
Output: <install-dir>/output/video/ltxv_scene_character/
```

ComfyUI processes them one at a time in the queue. On RTX 3060 at 249 frames, budget ~25 min per video. An overnight run of 18 videos = ~7–8 hours.

### Choosing frame count

Change `FRAMES` in the config:

| Frames | Duration | Generation time (RTX 3060) | Use for |
|--------|----------|---------------------------|---------|
| 97 | ~4 sec | ~5–8 min | Prompt testing, fast iteration |
| 177 | ~7 sec | ~12–15 min | Short clips |
| 249 | ~10 sec | ~20–25 min | Final content |

Must satisfy `8n + 1`. Common values: 97, 177, 201, 225, 249.

---

## Improving Character Consistency with LoRA Training

### The problem

Every video run re-interprets the character from the reference image. Over many videos the character's exact appearance drifts — slightly different hair, slightly different face shape. For a production pipeline where you want the same character across 20+ videos, this matters.

### The solution: LoRA fine-tuning

A LoRA is a small adapter trained on your character's images. After training, you include a trigger word in every prompt and the model reproduces the character accurately every time.

---

### Step 1 — Build your dataset

**Target: 30–50 images of your character.**

| Category | Count | What to capture |
|----------|-------|----------------|
| Full body, neutral pose | 15–20 | Overall look, outfit, proportions |
| Face close-ups | 10–15 | Face identity, different expressions |
| Different angles | 5–10 | Side view, 3/4 view, slight back turn |
| Different lighting | 5–10 | Makes the LoRA robust to scene lighting |

**For animated characters:**
- Pull clean stills from the source material
- Avoid motion blur, compression artifacts, or frames where the character is partially cut off
- Background doesn't matter — rembg will strip it during training prep

**Image prep checklist:**
- [ ] All images at least 512×512 (ideally 768×768 or higher)
- [ ] Character is clearly visible and in focus
- [ ] No watermarks, subtitles, or UI elements overlaid
- [ ] Consistent art style across all images (don't mix art styles)
- [ ] Remove any images where the character looks wrong or off-model

**Directory structure:**
```
lora_dataset/
├── images/
│   ├── 30_charname_style/       ← "30" = repeat count, affects training weight
│   │   ├── 001.png
│   │   ├── 002.png
│   │   └── ...
```

The folder name `30_charname_style` tells the trainer:
- `30` = repeat this folder's images 30 times per epoch (tune based on dataset size)
- `charname_style` = the trigger phrase you'll use in prompts

---

### Step 2 — Prepare captions

Each image needs a caption file (same name, `.txt` extension):

```
001.png  →  001.txt
```

Caption format:
```
charname_style, [describe what's in the image accurately]

# Examples:
charname_style, full body, red-haired anime girl in school uniform, neutral standing pose, white background
charname_style, face closeup, smiling expression, blue eyes, twin pigtails, soft lighting
charname_style, side view, walking pose, school bag on shoulder, outdoor setting
```

**Rules:**
- Always start with the trigger word (`charname_style`)
- Describe what's actually in the image — don't make things up
- Keep it factual: pose, expression, outfit details, setting
- Don't describe motion (it's a still image)

You can caption manually or use Florence2 (already installed in this setup) to auto-caption and then add the trigger word at the front.

**Auto-captioning with Florence2:**
```python
# rough example — adapt to your file paths
from PIL import Image
# load Florence2, generate caption, prepend trigger word, save .txt
```

---

### Step 3 — Train the LoRA

Full training instructions are in [FINETUNE_GUIDE.md](FINETUNE_GUIDE.md). Settings specific to a character LoRA:

```toml
# key settings in your training config

network_dim = 32          # LoRA rank — 16 for simple characters, 32 for detailed ones
network_alpha = 16        # half of network_dim is a good starting point

learning_rate = 1e-4
text_encoder_lr = 5e-5

max_train_steps = 800     # animated characters: 600–1000 is usually enough
save_every_n_steps = 200  # save checkpoints to find the best one

resolution = 512,512      # or 768,768 if your GPU can handle it
```

**Signs of good training:**
- At step 200–400: character starts appearing consistently
- At step 600–800: character is stable, details are sharp
- Overtrained (step 1000+): character looks plastic, loss of art style variation

Test checkpoints at 200, 400, 600, 800 — pick the one that looks most natural.

---

### Step 4 — Use the LoRA in your videos

Place the trained `.safetensors` file in `models/loras/`.

In every prompt, include the trigger word:

```
charname_style, laughing and jumping in a sunny forest,
bright eyes sparkling, smooth natural motion, cinematic quality, high detail
```

In the workflow, add a `LoRALoader` node between `UnetLoaderGGUF` and `LTXVImgToVideo`, and between `ClipLoaderGGUF` and `CLIPTextEncode`:

```
[UnetLoaderGGUF] ──► [LoRALoader] ──► model to LTXVImgToVideo
[ClipLoaderGGUF] ──► [LoRALoader] ──► clip to CLIPTextEncode
```

LoRA strength: start at `0.8`, go up to `1.0` if character isn't showing strongly enough.

---

### Step 5 — Batch generate with your LoRA

Once the LoRA is working, combine it with `batch_generate.py` for production:

```python
# In batch_generate.py, update your prompts to include the trigger word:

POSITIVE_PROMPTS = [
    "charname_style, laughing and jumping, forest background, smooth natural motion, cinematic quality",
    "charname_style, waving hello, city street background, joyful expression, high detail",
    "charname_style, dancing energetically, beach sunset, fluid motion, vibrant colors",
]

SCENES = [
    "forest_bg.png",
    "city_bg.png",
    "beach_bg.png",
    "mountain_bg.png",
    "indoor_bg.png",
]

SEEDS = [42, 123, 456]
# 3 scenes × 3 prompts × 3 seeds = 27 videos overnight
```

---

## Other Ways to Improve Output Quality

### Better scene images

The compositing quality depends on how well the character image and scene image match:

| Problem | Cause | Fix |
|---------|-------|-----|
| Character looks pasted on | Lighting mismatch | Choose scenes with similar lighting direction to character |
| Edges look rough | rembg mask quality | Use `isnet-general-use` model for complex hair or clothing |
| Character too big/small in scene | ImageScale size wrong | Adjust `width`/`height` in `ImageScale` node (node 14) |
| Character position wrong | x/y offset wrong | Adjust `x`, `y` in `ImageCompositeMasked` node (node 15) |

### Prompt engineering for motion

LTX-Video generates motion based on the prompt. Be specific:

| Vague (avoid) | Specific (use) |
|--------------|----------------|
| "dynamic motion" | "arms swinging forward, hair flowing left to right" |
| "she is happy" | "laughing with mouth open, eyes crinkling, cheeks raised" |
| "walking" | "taking long confident strides, shoulders swaying naturally" |
| "dancing" | "spinning with arms raised, skirt fanning out, head tilting back" |

### Seed strategy

- Find one seed that produces good character motion → use it as your "base" seed
- Generate variations: `base_seed`, `base_seed + 1`, `base_seed + 2`
- Small seed increments produce related but distinct variations
- Large seed jumps produce completely different motion

### Post-processing

The raw output is 768×512. For sharper final content:

1. **Upscale** — run through Real-ESRGAN or TopazVideo AI for 2×/4× upscaling
2. **Stabilize** — video stabilization if there's unwanted camera shake
3. **Color grade** — adjust contrast/saturation if the scene colors clash with the character

---

## Production Workflow Summary

For consistent character video content at scale:

```
1. Collect 30–50 character stills
         │
2. Caption + prepare dataset
         │
3. Train LoRA (600–800 steps)
         │
4. Test LoRA with 3–4 test prompts
         │
5. Build SCENES list (background images)
6. Build PROMPTS list (actions + trigger word)
7. Set SEEDS list (2–3 per combo)
         │
8. Run: python3 batch_generate.py
         │
9. Leave overnight → collect videos
         │
10. Post-process best outputs
```

Once the LoRA is trained (one-time cost), steps 5–10 are repeatable indefinitely with new scenes and prompts.

---

## File Reference

| File | Purpose |
|------|---------|
| `batch_generate.py` | Queue multiple videos in one run |
| `queue_test.py` | Queue a single video via API |
| `workflows/ltxv_096_gguf_scene_character.json` | Auto BG removal + scene composite workflow |
| `workflows/ltxv_096_gguf_i2v_dual_image.json` | Manual composite workflow |
| `workflows/ltxv_096_gguf_i2v.json` | Single image → video workflow |
| `custom_nodes/rembg_node/__init__.py` | RemoveBackgroundRembg node |
| `FINETUNE_GUIDE.md` | Full LoRA training instructions |
| `DUAL_IMAGE_GUIDE.md` | Manual composite workflow guide |
| `USER_GUIDE.md` | Base workflow node-by-node guide |
