# Dual Image Guide — Character + Scene Video

This guide explains how to give the AI two images — a **character** (a person) and a **scene** (a background/location) — and generate a video of that character moving inside that scene.

---

## What This Does

Instead of animating a single photo, you provide two images that get composited together before animation:

```
  Character Photo        Scene / Background         Combined Image
  ┌────────────┐        ┌────────────────────┐     ┌────────────────────┐
  │            │        │                    │     │                    │
  │   👧 photo │   +    │  🌳 park / room    │  =  │  👧 standing in 🌳 │
  │  passport  │        │  background image  │     │                    │
  └────────────┘        └────────────────────┘     └──────────┬─────────┘
                                                               │
                                                               ▼
                                                         🎬 Animated Video
```

---

## What Changed from the Single Image Workflow

| | Original workflow | Dual image workflow |
|---|---|---|
| **Input images** | 1 (character/photo) | 2 (character + scene) |
| **New nodes added** | — | `LoadImage` (scene), `ImageScale`, `ImageCompositeMasked` |
| **Workflow file** | `ltxv_096_gguf_i2v.json` | `ltxv_096_gguf_i2v_dual_image.json` |
| **Everything else** | same | same |

Only 3 nodes were added. The rest of the pipeline — models, sampler, VAE, output — is identical.

---

## The New Pipeline — Block Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MODEL LOADERS (unchanged)                         │
│  [UnetLoaderGGUF]   [ClipLoaderGGUF]   [VaeGGUF]                          │
└──────┬──────────────────────┬────────────────┬────────────────────────────┘
       │                      │                │
┌──────┴──────────────────────┴────────────────┴────────────────────────────┐
│                        IMAGE COMPOSITING  (NEW)                            │
│                                                                            │
│  ┌───────────────────────┐      ┌─────────────────────────────────────┐   │
│  │  LoadImage            │      │  LoadImage                          │   │
│  │  "Character Image"    │      │  "Scene / Background Image"         │   │
│  │                       │      │                                     │   │
│  │  Your person's photo  │      │  A park, room, street, fantasy      │   │
│  │  PNG with transparent │      │  landscape — any background you     │   │
│  │  bg gives best edges  │      │  want the character placed in       │   │
│  └──────┬──────────┬─────┘      └──────────────────┬──────────────────┘   │
│         │ IMAGE    │ MASK                           │ IMAGE                │
│         ▼          │                                │                      │
│  ┌──────────────┐  │                                │                      │
│  │  ImageScale  │  │                                │                      │
│  │              │  │                                │                      │
│  │  Resize the  │  │                                │                      │
│  │  character   │  │                                │                      │
│  │  to fit the  │  │                                │                      │
│  │  scene       │  │                                │                      │
│  └──────┬───────┘  │                                │                      │
│         │ IMAGE    │ MASK                           │ IMAGE                │
│         └──────────┼────────────────────────────────┘                      │
│                    ▼                                                        │
│         ┌──────────────────────────┐                                       │
│         │   ImageCompositeMasked   │                                       │
│         │                          │                                       │
│         │  Places the character    │                                       │
│         │  onto the scene at the   │                                       │
│         │  x, y position you set   │                                       │
│         └──────────┬───────────────┘                                       │
└────────────────────┼───────────────────────────────────────────────────────┘
                     │ Composited IMAGE
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│              ANIMATION PIPELINE (unchanged from original)                  │
│                                                                            │
│  [CLIPTextEncode x2] → [LTXVConditioning] → [LTXVImgToVideo]              │
│                                                     │                      │
│                                              [KSampler]                    │
│                                                     │                      │
│                                             [VAEDecode]                    │
│                                                     │                      │
│                                    [CreateVideo] → [SaveVideo]             │
└────────────────────────────────────────────────────────────────────────────┘
                                          │
                                    🎬 Your Video
                         Character animated inside the scene
```

---

## The Three New Nodes

### 1. LoadImage — Scene / Background Image

Loads the background. Can be any image: a real photo of a park, a room interior, an AI-generated landscape, anything.

| Setting | What it does |
|---------|-------------|
| Image | Click to upload your scene/background image |

**What makes a good scene image:**
- Clear, recognisable background
- Resolution close to your target (768×512 for landscape, 512×768 for portrait)
- Not too busy — simpler backgrounds composite cleaner
- Match the lighting to the character if possible

---

### 2. ImageScale — Scale Character to Fit Scene

Resizes the character photo so it's the right size relative to the background.

| Parameter | Default | What it means | When to change |
|-----------|---------|---------------|----------------|
| `upscale_method` | bilinear | How to resize pixels | Keep as bilinear |
| `width` | 256 | Character width in pixels | Increase for larger character in scene |
| `height` | 320 | Character height in pixels | Adjust to match character's aspect ratio |
| `crop` | center | How to handle aspect ratio mismatch | "disabled" preserves ratio, "center" crops |

**Sizing guide:**

| Scene size | Character feels small | Character feels natural | Character feels large |
|------------|----------------------|------------------------|----------------------|
| 768×512    | 128×160              | 256×320                | 384×480              |
| 512×768    | 160×200              | 256×320                | 384×480              |

If your character photo is portrait (tall), keep `height` larger than `width`. If it's square (passport), use equal or close values.

---

### 3. ImageCompositeMasked — Place Character onto Scene

This is the compositing node. It pastes the scaled character onto the scene at a position you choose.

| Parameter | Default | What it means | When to change |
|-----------|---------|---------------|----------------|
| `x` | 256 | Horizontal position (pixels from left) | Move character left or right |
| `y` | 96 | Vertical position (pixels from top) | Move character up or down |
| `resize_source` | false | Auto-resize character to match scene | Keep false — use ImageScale instead |

**Positioning guide (for 768×512 scene):**

```
     0                384                768
   0 ┌──────────────────────────────────────┐
     │                                      │
     │    ← left side    │   right side →   │
 256 │                                      │
     │                  bottom              │
 512 └──────────────────────────────────────┘

To center a 256px wide character:   x = (768 - 256) / 2 = 256
To place left third:                x = 80
To place right third:               x = 430
To place near top:                  y = 30
To place at bottom:                 y = 512 - character_height - 20
```

**The MASK input:**
The `ImageCompositeMasked` node uses the MASK from your character LoadImage to blend edges cleanly.

- **PNG with transparent background**: mask is the alpha channel — edges are clean, background is invisible
- **JPEG / PNG without transparency**: mask is all white — character pastes as a hard rectangle (background of the photo is included)

For best results, use a PNG where the background has been removed. See the "Removing the background" section below.

---

## How to Use the Workflow

**Step 1** — Load the workflow in ComfyUI
- Open `ltxv_096_gguf_i2v_dual_image` from the workflow browser

**Step 2** — Upload your character image
- Click the `Character Image` LoadImage node
- Upload your photo (PNG with transparent background gives cleanest results)

**Step 3** — Upload your scene image
- Click the `Scene / Background Image` LoadImage node
- Upload your background photo or AI-generated scene

**Step 4** — Adjust character size and position
- In `ImageScale`: set `width` and `height` to how large the character should appear
- In `ImageCompositeMasked`: set `x` and `y` to position the character in the scene

**Step 5** — Update your prompt
- Mention the scene in your prompt: "A girl laughing in a sunlit park, gentle breeze..."
- Keep the motion description from the original workflow

**Step 6** — Queue and generate

---

## Removing the Background from Character Photo

For clean compositing, the character image should have a transparent background. Three options:

### Option A — Do it in ComfyUI (recommended if you have a dedicated node)

If you have a background removal node installed (like BiRefNet), add it between `LoadImage` and `ImageScale`:

```
[LoadImage Character] → [BiRefNet / RemBG] → [ImageScale] → [ImageCompositeMasked]
```

This is not included in the current workflow but can be added manually.

### Option B — Remove background before uploading

Use a free online tool:
- remove.bg
- Adobe Express background remover
- Canva background remover

Download the result as PNG (preserves transparency) and use that as your character image.

### Option C — Use JPEG anyway (rectangular paste)

If you don't remove the background, the character photo's background will be pasted as a rectangle onto the scene. This looks less natural but still works for testing. The AI may blend it somewhat during video generation.

---

## Prompt Strategy for Dual Images

Since the character is now in a specific scene, your prompt should describe both:

```
[character] [action], [scene/environment detail], [lighting], smooth natural motion, cinematic quality
```

**Example:**
```
A cheerful young girl laughing joyfully in a sunny park, trees and green grass behind her,
golden afternoon light, head tilting side to side, eyes sparkling, smooth natural motion,
cinematic quality, high detail
```

**What to include:**
- Reference the scene ("in a sunny park", "inside a cosy room")
- Keep the motion description detailed
- Match the lighting in your prompt to the actual lighting in the scene image

---

## What to Expect

| Scenario | Expected result |
|----------|----------------|
| PNG character with transparent bg + matching scene | Clean composite, natural-looking video |
| JPEG character + scene | Rectangular paste visible, AI may soften it somewhat |
| Mismatched lighting (bright character, dark scene) | Visible mismatch — use similar-lit images |
| Character too large for scene | Feels claustrophobic, reduce width/height in ImageScale |
| Character too small | Hard to see motion, increase width/height in ImageScale |

The AI animates the **composited image** as a whole. It doesn't know separately that one part is the character and one is the scene — it sees one merged image. The more natural the composite looks, the more natural the video will be.

---

## Common Issues and Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Character has white box around it | JPEG used, no alpha/mask | Remove background first, use PNG |
| Character position wrong | x/y values off | Adjust `x` and `y` in ImageCompositeMasked |
| Character too big / too small | Scale values off | Adjust `width`/`height` in ImageScale |
| Lighting mismatch visible | Different light conditions in source images | Use images shot in similar lighting |
| Character blends into background | Similar colours | Adjust position or use a more contrasting scene |
| Scene is deformed in video | Scene resolution too different from 768×512 | Resize scene image to 768×512 before uploading |

---

## Quick Reference

```
Character too big?     → decrease width/height in ImageScale
Character too small?   → increase width/height in ImageScale
Character too far left?  → increase x in ImageCompositeMasked
Character too far right? → decrease x in ImageCompositeMasked
Character too high?    → decrease y in ImageCompositeMasked
Character too low?     → increase y in ImageCompositeMasked
Edges look bad?        → use PNG with transparent background
Scene looks squished?  → resize scene to 768×512 before upload
```
