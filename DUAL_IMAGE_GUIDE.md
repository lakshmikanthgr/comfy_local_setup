# Dual Image Guide — Character + Scene Video

Animate a person inside a background/scene by providing two images: a character photo and a scene image.

---

## Two Workflows — Pick One

| Workflow | File | Best for |
|----------|------|---------|
| **Auto BG Removal** | `ltxv_096_gguf_scene_character.json` | Any JPEG or PNG — background removed automatically |
| **Manual composite** | `ltxv_096_gguf_i2v_dual_image.json` | You already have a PNG with transparent background |

**Start with the auto workflow.** It handles everything internally.

---

## What These Workflows Do

```
  Your character photo       Your scene image           Final video
  ┌──────────────────┐      ┌──────────────────────┐   ┌─────────────────────────┐
  │  📷 any photo    │  +   │  🌳 park / room /    │ → │  👧 animated inside 🌳  │
  │  JPEG or PNG     │      │      location         │   │  ~10 seconds            │
  └──────────────────┘      └──────────────────────┘   └─────────────────────────┘
```

---

## Auto BG Removal Workflow — Full Pipeline

`ltxv_096_gguf_scene_character.json`

```
┌────────────────────────────────────────────────────────────────────────┐
│                     MODEL LOADERS (unchanged)                          │
│  [UnetLoaderGGUF]   [ClipLoaderGGUF]   [VaeGGUF]                     │
└─────┬────────────────────┬──────────────────┬──────────────────────────┘
      │                    │                  │
┌─────┴────────────────────┴──────────────────┴──────────────────────────┐
│             CHARACTER PIPELINE (NEW in this feature)                   │
│                                                                        │
│  ┌─────────────────────┐                                               │
│  │  LoadImage          │  ← upload any photo (JPEG or PNG)            │
│  │  "Character Image"  │                                               │
│  └──────────┬──────────┘                                               │
│             │ IMAGE                                                    │
│             ▼                                                          │
│  ┌─────────────────────┐                                               │
│  │  RemoveBackground   │  ← our custom node (rembg_node)              │
│  │  model: u2net_      │    downloads ~170MB u2net model on first use  │
│  │  human_seg          │                                               │
│  └──────┬──────────────┘                                               │
│         │ IMAGE (no bg)    │ MASK (alpha)                             │
│         ▼                  │                                          │
│  ┌──────────────────┐      │                                          │
│  │  ImageScale      │      │   ┌──────────────────────────────────┐  │
│  │  256×320 px      │      │   │  LoadImage                       │  │
│  └──────────┬───────┘      │   │  "Scene / Background Image"      │  │
│             │ IMAGE        │   └──────────────────┬───────────────┘  │
│             └──────────────┼────────────────────  │ IMAGE            │
│                            ▼                      ▼                  │
│                 ┌──────────────────────────────────────────────────┐ │
│                 │           ImageCompositeMasked                    │ │
│                 │  Pastes character onto scene with clean edges     │ │
│                 └──────────────────────┬─────────────────────────  ┘ │
└────────────────────────────────────────┼───────────────────────────────┘
                                         │ Composited IMAGE
                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│             ANIMATION PIPELINE (same as all other workflows)           │
│                                                                        │
│  [LTXVImgToVideo] → [KSampler] → [VAEDecode] → [CreateVideo+SaveVideo]│
└────────────────────────────────────────────────────────────────────────┘
```

---

## The RemoveBackground Node

This is a custom node (`custom_nodes/rembg_node/`) included in this repo. It wraps the `rembg` Python library.

| Parameter | Options | Default | What it does |
|-----------|---------|---------|-------------|
| `model` | `u2net_human_seg` | ✓ | Best for people/portraits — trained specifically on humans |
| | `u2net` | | General purpose — works on any subject |
| | `isnet-general-use` | | Newer model, slightly better on complex edges |

**First run**: downloads the model weights (~170MB) automatically to `~/.u2net/`. Subsequent runs use the cached file.

**Which model to use:**
- Portrait of a person → `u2net_human_seg` (default, best for your use case)
- Object, animal, or non-human subject → `u2net`
- Best possible quality, slower → `isnet-general-use`

---

## Compositing Parameters

### ImageScale — Set Character Size

Controls how large the character appears in the scene.

| Parameter | Default | What it means |
|-----------|---------|---------------|
| `width` | 256 | Character width in pixels after scaling |
| `height` | 320 | Character height in pixels after scaling |
| `upscale_method` | bilinear | Resize algorithm — keep as bilinear |
| `crop` | center | How to handle aspect mismatch |

**Sizing reference for 768×512 scene:**

| Character feels | width × height |
|-----------------|---------------|
| Small / distant | 128 × 160 |
| Natural / mid   | 256 × 320 |
| Large / close   | 384 × 480 |

Adjust to match how the character would naturally appear in the scene.

### ImageCompositeMasked — Set Character Position

Controls where the character is placed in the scene.

| Parameter | Default | What it means |
|-----------|---------|---------------|
| `x` | 256 | Pixels from left edge of scene |
| `y` | 96 | Pixels from top edge of scene |
| `resize_source` | false | Keep false — use ImageScale for sizing |

**Positioning cheat sheet (768×512 scene, 256px wide character):**

```
Center:         x = (768 - 256) / 2 = 256
Left third:     x = 80
Right third:    x = 430
Top area:       y = 30
Center height:  y = (512 - 320) / 2 = 96
Near bottom:    y = 512 - 320 - 20 = 172
```

---

## How to Use

**Step 1** — Open `ltxv_096_gguf_scene_character` from the ComfyUI workflow browser

**Step 2** — Upload your character image (node: "Character Image — any format")
- JPEG, PNG, anything — background is removed automatically

**Step 3** — Upload your scene/background image (node: "Scene / Background Image")
- A park, room, street, or any background you want

**Step 4** — Adjust size and position
- `ImageScale`: set `width`/`height` to how large the character should be
- `ImageCompositeMasked`: set `x`/`y` to where in the scene

**Step 5** — Update the positive prompt to mention the scene
```
A cheerful girl laughing joyfully in a sunny park, trees and light
behind her, warm golden light, smooth natural motion, high detail
```

**Step 6** — Queue and generate

---

## What Makes a Good Scene Image

| Works well | Avoid |
|-----------|-------|
| Clear, recognisable background | Busy, cluttered backgrounds |
| Matches the lighting of the character photo | Very different lighting (bright outdoor char + dark indoor scene) |
| 768×512 or close to it | Very different aspect ratio (needs rescaling) |
| Simple colour palette | Too many competing focal points |

The AI animates the composited image as one. The better the composite looks, the more natural the video.

---

## Prompting for Dual Image

Describe both the character action AND the scene in the positive prompt:

```
[character] [action], [scene description], [lighting], smooth natural motion, cinematic quality
```

**Example for girl + park:**
```
A cheerful 3 year old girl laughing with pure joy in a sunny park,
trees and green grass in the background, golden afternoon light,
head tilting side to side, eyes sparkling, smooth natural motion,
cinematic portrait, high detail, vibrant colors
```

Add `bad compositing, visible seams` to the negative prompt.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `RemoveBackground` node not found | Custom node not loaded | Restart ComfyUI; check terminal for rembg_node import errors |
| Background removal is slow | u2net model downloading on first run | Wait ~30 sec for download, cached after |
| Character edges are rough | rembg limitation on complex hair/fur | Try `isnet-general-use` model in RemoveBackground |
| Character looks pasted / lighting mismatch | Different lighting in the two photos | Use photos with similar lighting conditions |
| Character position wrong | x/y values off | Adjust in `ImageCompositeMasked` |
| Character too big / small | Scale values off | Adjust `width`/`height` in `ImageScale` |
| Memory error | 249 frames too heavy | Reduce `length` to 177 in `LTXVImgToVideo` |

---

## Quick Reference

```
BG not removed properly?    → switch model to "isnet-general-use"
Character too big?          → reduce width/height in ImageScale
Character too small?        → increase width/height in ImageScale
Position wrong?             → adjust x/y in ImageCompositeMasked
Lighting looks off?         → use photos shot in similar conditions
Scene looks squished?       → resize scene image to 768×512 before upload
Memory error?               → reduce frame length from 249 to 177
```
