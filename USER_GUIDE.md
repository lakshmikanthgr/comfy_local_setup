# User Guide — LTX-Video Image-to-Video

This guide explains how the setup works, what every piece does, and what you can change to get different results. No technical background needed.

---

## What Does This Do?

You give it **one photo**. It gives you back a **short video** of that photo coming to life — the person smiling, the scene moving, the light shifting. You describe the motion in plain English and the AI figures out how to animate it.

```
   Your Photo          Your Description            Output Video
  ┌──────────┐     "girl laughing, head         ┌──────────────┐
  │  📷      │  +   tilting, eyes sparkling"  → │  🎬  ~10 sec │
  └──────────┘                                   └──────────────┘
```

---

## How It Works — The Full Pipeline

Every box below is a **node** in ComfyUI. Data flows left to right, top to bottom.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MODEL LOADERS                                │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  UnetLoaderGGUF  │  │ ClipLoaderGGUF   │  │    VaeGGUF       │  │
│  │                  │  │                  │  │                  │  │
│  │  The main AI     │  │  Reads your text │  │  Converts images │  │
│  │  brain. Knows    │  │  prompts into    │  │  into a compact  │  │
│  │  how video       │  │  numbers the AI  │  │  math format     │  │
│  │  motion works.   │  │  understands.    │  │  (latent space)  │  │
│  └───────┬──────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└──────────┼──────────────────────┼─────────────────────┼────────────┘
           │                      │                      │
           │            ┌─────────┴──────────┐          │
           │            │   CLIPTextEncode   │          │
           │            │   (×2)             │          │
           │            │                   │          │
           │            │  Positive Prompt  │          │
           │            │  "girl laughing…" │          │
           │            │                   │          │
           │            │  Negative Prompt  │          │
           │            │  "blurry, frozen…"│          │
           │            └─────────┬──────────┘          │
           │                      │                      │
           │            ┌─────────▼──────────┐          │
           │            │  LTXVConditioning  │          │
           │            │                   │          │
           │            │  Stamps the video │          │
           │            │  with frame rate  │          │
           │            │  (25fps)          │          │
           │            └─────────┬──────────┘          │
           │                      │                      │
           │      ┌───────────────▼──────────────────┐  │
           │      │         LTXVImgToVideo            │  │
           │      │                                  │◄─┘ (VAE)
           │      │  Takes your photo + prompts and  │
           │      │  builds the starting point for   │◄── Your Photo
           │      │  the video in latent space.      │
           │      │  Sets resolution and length.     │
           │      └───────────────┬──────────────────┘
           │                      │
           │      ┌───────────────▼──────────────────┐
           └─────►│            KSampler              │
                  │                                  │
                  │  The generation engine.          │
                  │  Runs the AI model step by step, │
                  │  gradually turning noise into    │
                  │  your video frames.              │
                  └───────────────┬──────────────────┘
                                  │
                  ┌───────────────▼──────────────────┐
                  │           VAEDecode               │
                  │                                  │
                  │  Converts the latent space        │
                  │  result back into real pixels.    │
                  └───────────────┬──────────────────┘
                                  │
                  ┌───────────────▼──────────────────┐
                  │    CreateVideo  →  SaveVideo      │
                  │                                  │
                  │  Stitches all frames into an MP4  │
                  │  and saves it to output/          │
                  └───────────────┬──────────────────┘
                                  │
                             🎬 Your Video
```

---

## What Each Node Does (Plain English)

### Model Loaders

| Node | What it loads | Why it matters |
|------|--------------|----------------|
| `UnetLoaderGGUF` | `ltxv-2b-0.9.6-distilled-q6_k.gguf` | The main AI model. This is the brain that has learned how real-world motion looks. GGUF format means it's compressed to fit on a 12GB GPU. |
| `ClipLoaderGGUF` | `t5xxl_fp32-q4_0.gguf` | Translates your English text into numbers. The AI doesn't read English — this converts "girl laughing" into a format it understands. |
| `VaeGGUF` | `pig_video_enhanced_vae_fp32-f16.gguf` | A compression/decompression tool. It squishes your image into a tiny math space for the AI to work in, then expands it back into pixels. |

---

### Prompt Nodes (CLIPTextEncode × 2)

These are where you type what you want.

**Positive Prompt** — describe what you WANT to see happen:
```
A cheerful 3 year old girl laughing with pure joy, bright eyes sparkling,
wide natural smile, head tilting side to side playfully, shoulders bouncing
with giggles, soft warm golden lighting, smooth natural motion, high detail
```

**Negative Prompt** — describe what you DON'T want:
```
worst quality, blurry, flickering, distorted face, frozen, lifeless expression,
morphing face, choppy, unnatural motion
```

> **Tip**: The positive prompt should describe *motion*, not just appearance.
> "Eyes sparkling" is appearance. "Head tilting side to side" is motion. Motion descriptions matter most.

---

### LTXVConditioning

Stamps the video with timing information (frame rate). You almost never need to change this.

| Parameter | Default | What it means |
|-----------|---------|---------------|
| `frame_rate` | 25 | Frames per second. 25fps is standard film/video. Higher = smoother but changes timing. |

---

### LTXVImgToVideo

This is the node that makes this an **image-to-video** workflow. It takes your photo and sets up the video dimensions.

| Parameter | Default | What it means | When to change |
|-----------|---------|---------------|----------------|
| `width` | 768 | Video width in pixels | Lower (512) if you get memory errors |
| `height` | 512 | Video height in pixels | Use 512×768 for portrait/vertical photos |
| `length` | 249 | Number of frames (~10 sec at 25fps) | See frame table below |
| `batch_size` | 1 | How many videos to generate at once | Keep at 1 on 12GB GPU |
| `strength` | 1.0 | How much the image influences the video | Lower = more creative/less faithful to photo |

**Frame length options** (must follow the rule: 8×N+1):

| Frames | Duration | Use when |
|--------|----------|----------|
| 97 | ~4 sec | Quick test, fastest |
| 177 | ~7 sec | Good balance |
| 201 | ~8 sec | Recommended default |
| 249 | ~10 sec | Full length (may need 12GB+) |

**Strength explained:**
- `1.0` = the video starts exactly from your photo and animates from there (recommended)
- `0.8` = gives the AI more creative freedom, may deviate from the photo
- `0.5` = the photo is just a rough guide, AI invents more

---

### KSampler

The generation engine. This is where the actual AI computation happens.

| Parameter | Default | What it means | When to change |
|-----------|---------|---------------|----------------|
| `seed` | 42 | Random starting point | Change this to get a different result from the same prompt |
| `control_after_generate` | fixed | What to do with seed after each run | Set to "increment" to auto-try different seeds |
| `steps` | 8 | How many refinement passes the AI makes | 6–12 range. More steps ≠ always better for this model |
| `cfg` | 1.0 | How strictly the AI follows your prompt | Keep at 1.0 — this is a distilled model |
| `sampler_name` | euler | The mathematical method for generation | Don't change — euler is correct for LTX-Video |
| `scheduler` | sgm_uniform | How noise is reduced across steps | Don't change — sgm_uniform is correct for LTX-Video |
| `denoise` | 1.0 | How much of the image to re-generate | Keep at 1.0 for video generation |

> **Why cfg=1.0?** This model is "distilled" — a compressed version trained to work with minimal guidance. Setting CFG higher (like 7.0 as you might for image generators) actually makes results *worse*. 1.0 is correct.

> **Why only 8 steps?** Same reason. Distilled models bake many steps into one. 8 steps here is equivalent to ~50 steps in a non-distilled model.

**The only parameter you should regularly change: `seed`**
Every seed gives a different animation from the same photo and prompt. If you don't like the result, change the seed first before adjusting anything else.

---

### VAEDecode

Converts the AI's internal math representation back into real pixels. No user-adjustable parameters.

---

### CreateVideo

Assembles all the individual frames into a video.

| Parameter | Default | What it means |
|-----------|---------|---------------|
| `fps` | 25 | Playback speed. Must match `frame_rate` in LTXVConditioning |

---

### SaveVideo

Saves the final MP4 file.

| Parameter | Default | What it means |
|-----------|---------|---------------|
| `filename_prefix` | `video/ltxv_i2v` | Where the file is saved inside the `output/` folder |
| `format` | auto | Video container format |
| `codec` | auto | Compression codec |

Output files appear in: `ComfyUI/output/video/ltxv_i2v/`

---

## Parameters to Tune (Priority Order)

When a result doesn't look right, change these in this order:

1. **Seed** — try 3–5 different seeds before changing anything else
2. **Positive prompt** — add more specific motion words
3. **Negative prompt** — add whatever artifact you're seeing ("frozen face", "flickering")
4. **Steps** — try 10 or 12 if motion looks incomplete
5. **Strength** — lower slightly (0.9) if the AI is ignoring your photo
6. **Length** — reduce if you hit memory errors

---

## Common Results and Fixes

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| Video is barely moving / frozen | Prompt has no motion words | Add specific movement: "head turning", "eyes blinking", "hair moving" |
| Face looks distorted or melting | Seed producing bad output | Change the seed |
| Out of memory error | Frame length too high | Reduce `length` from 249 to 177 |
| Video is too dark or washed out | Lighting in input photo | Mention lighting in prompt: "soft warm lighting" |
| Motion is jerky / choppy | Too few steps | Increase steps to 10–12 |
| Person doesn't look like the photo | Strength too low | Set `strength` back to 1.0 |

---

## Where Files Go

```
comfyui-ltxv/                     ← ComfyUI root
├── models/
│   ├── unet/                     ← main AI model (.gguf)
│   ├── clip/                     ← text encoder (.gguf)
│   └── vae/                      ← image encoder (.gguf)
├── output/
│   └── video/ltxv_i2v/           ← your generated videos land here
└── user/default/workflows/
    └── ltxv_096_gguf_i2v.json    ← the workflow (pre-loaded)
```

---

## Quick Reference Card

```
Want longer video?     → increase LTXVImgToVideo → length (must be 8n+1)
Different result?      → change KSampler → seed
More faithful to photo → increase LTXVImgToVideo → strength (max 1.0)
More motion?           → add more action words to positive prompt
Less distortion?       → add "distorted face, morphing" to negative prompt
Portrait photo?        → swap width/height: 512 wide × 768 tall
Memory error?          → reduce length to 177 or lower width/height
```
