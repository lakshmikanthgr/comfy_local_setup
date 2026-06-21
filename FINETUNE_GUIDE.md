# Fine-Tuning Guide — Teaching LTX-Video Your Content

This guide explains how to train LTX-Video on your own images and videos so it generates results specific to your subject — a person, a place, a style, or a movement type.

---

## What Fine-Tuning Actually Does

Out of the box, LTX-Video knows how motion works in general — people walk, water flows, leaves blow. But it has never seen *your daughter*, *your home*, or *your specific style*.

Fine-tuning shows the model many examples of your specific content and adjusts its internal weights so it gets much better at generating that specific thing.

```
Before fine-tuning:                After fine-tuning:
"girl laughing" →                  "girl laughing" →
  generic child                      your daughter, her
  animation                          real expressions,
                                     her face accurately
```

---

## Two Approaches: LoRA vs Full Fine-Tune

| | LoRA | Full Fine-Tune |
|---|---|---|
| What it does | Trains a small adapter on top of the model | Retrains the whole model |
| File size | 50–200 MB | ~5 GB (full model) |
| GPU needed | 12GB (tight but feasible) | 40GB+ |
| Training time | 1–4 hours | Days |
| Quality | Very good for specific subjects | Best possible |
| Portability | Load alongside the base model | Replaces the base model |
| **Recommendation** | **Use this** | Not practical for your GPU |

**LoRA** is what you want. It produces a small file that "steers" the base model toward your content without replacing it.

---

## The Overall Process

```
  Your Photos/Videos
         │
         ▼
  ┌─────────────────┐
  │  Data Prep      │  Collect, caption, resize, format
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Get Safetensors│  Download the non-quantized model
  │  Model          │  (GGUF can't be trained directly)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  LoRA Training  │  Run training script, ~1-4 hours
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  LoRA File      │  A .safetensors file, 50-200MB
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Use in ComfyUI │  Load LoRA alongside base model
  └────────┬────────┘
           │
           ▼
    Videos of YOUR content
```

---

## Step 1 — Collect Your Training Data

### What kind of data you need

For a **specific person** (most common use case):
- Short video clips (3–10 seconds each) of the person
- OR a sequence of photos showing different expressions, angles, lighting
- Minimum: 20–30 clips. Better: 50–100 clips.
- Show variety: different expressions, head angles, lighting conditions

For a **specific place or scene**:
- Videos of the location at different times, angles, movements
- 20–50 clips

For a **movement style** (e.g., a specific dance, gesture):
- Clear recordings of that movement
- Multiple performers doing the same thing helps generalise

### What makes good training data

```
✓ Good                          ✗ Avoid
─────────────────────────────   ──────────────────────────────
Clear, well-lit subject         Blurry or dark footage
Consistent resolution           Mixed resolutions
Varied angles and expressions   All the same pose
3–10 second clips               Very long clips (>30 sec)
Natural, real motion            Sped up or slowed footage
Clean background (optional)     Heavy filters or edits
```

### Format and resolution

- **Format**: MP4 (H.264)
- **Resolution**: 512×512 or 768×512 (same as your inference resolution)
- **Frame rate**: 24 or 25fps
- **Length per clip**: 3–10 seconds (72–250 frames)

If you only have photos (not video), you can still train — see the "Training from Images" section below.

---

## Step 2 — Write Captions

Every training clip needs a text description. This teaches the model what to associate with what.

### Caption format that works well

```
[subject description], [action/motion], [environment], [quality tags]
```

**Examples:**
```
A young girl with brown hair and bright eyes, laughing joyfully,
head tilting side to side, soft indoor lighting, high quality video

A young girl with brown hair, blinking slowly and smiling,
looking slightly to the left, warm natural lighting, cinematic

A young girl with brown hair, mouth opening in surprise then
breaking into a wide smile, soft lighting, high detail
```

**Rules for good captions:**
- Describe the motion explicitly, not just the appearance
- Keep descriptions consistent — use the same name/description for the same person across all clips
- Use a **trigger word** — a unique phrase that becomes associated with your subject (e.g., "zephyr girl" or "mia_child"). Add it to every caption.
- 1–3 sentences per clip is enough

### Caption trigger word

Pick something unique that doesn't appear in everyday language. Add it to the start of every caption:

```
"zephyr_girl laughing joyfully, head tilting..."
"zephyr_girl blinking slowly, soft smile..."
"zephyr_girl looking surprised, then smiling..."
```

At inference time, include `zephyr_girl` in your prompt and the LoRA will activate your subject.

---

## Step 3 — Prepare the Dataset Folder

Organise files so each video has a matching caption file with the same name:

```
training_data/
├── clip_001.mp4
├── clip_001.txt          ← caption for clip_001.mp4
├── clip_002.mp4
├── clip_002.txt
├── clip_003.mp4
├── clip_003.txt
...
```

The `.txt` file contains just the caption text, nothing else.

---

## Step 4 — Get the Non-Quantized Model

GGUF files are compressed for inference only — you cannot train on them. You need the original safetensors version for training.

Download `ltxv-2b-0.9.6-distilled.safetensors` from `Lightricks/LTX-Video` on Hugging Face.

You also need the VAE and text encoder in safetensors format:
- `ltxv-2b-0.9.5-vae.safetensors`
- `t5xxl_fp16.safetensors` (or fp8 to save memory)

Place these in a `training_models/` directory — separate from your inference models.

---

## Step 5 — Set Up the Training Environment

The official training code is in the `Lightricks/LTX-Video` repository (separate from the ComfyUI plugin). Clone it:

```bash
git clone https://github.com/Lightricks/LTX-Video.git ltxv-training
cd ltxv-training
pip install -e ".[training]"
```

Confirm your GPU is visible:
```bash
python -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory // 1024**3, 'GB')"
```

---

## Step 6 — Training Configuration

Create a config file `my_lora_config.yaml`:

```yaml
# Model paths
model_path: ./training_models/ltxv-2b-0.9.6-distilled.safetensors
vae_path: ./training_models/ltxv-2b-0.9.5-vae.safetensors
text_encoder_path: ./training_models/t5xxl_fp16.safetensors

# Dataset
data_path: ./training_data/
caption_extension: .txt

# Output
output_dir: ./lora_output/
output_name: my_subject_lora

# LoRA settings
lora_rank: 32            # Higher = more capacity, more VRAM. 16-64 range.
lora_alpha: 32           # Usually same as rank

# Training
resolution: [512, 768]   # [width, height] — match your inference resolution
num_frames: 49           # frames per training clip (must be 8n+1)
batch_size: 1            # Keep at 1 for 12GB GPU
gradient_checkpointing: true    # Required for 12GB GPU
mixed_precision: bf16    # Saves memory, minimal quality loss

# Optimiser
learning_rate: 1e-4      # Start here; lower if training unstable
max_train_steps: 1000    # ~500 steps per 10 clips is a rough guide
save_every_n_steps: 200  # Save checkpoints to evaluate progress

# Memory optimisations for 12GB GPU
enable_xformers: true
gradient_accumulation_steps: 4
```

### Key parameters explained

| Parameter | What it does | 12GB GPU guidance |
|-----------|-------------|-------------------|
| `lora_rank` | Capacity of the LoRA. Higher = learns more but needs more VRAM. | Start at 16, try 32 if memory allows |
| `learning_rate` | How fast the model learns. Too high = unstable. Too low = slow. | 1e-4 is a safe start |
| `max_train_steps` | Total training iterations. More data = more steps needed. | 500–2000 depending on dataset size |
| `num_frames` | How many frames per clip used in training. | 49 (≈2 sec) is memory-efficient |
| `gradient_checkpointing` | Trades compute for memory. Slower but fits in 12GB. | Always enable |
| `batch_size` | Clips processed at once. | Keep at 1 |
| `gradient_accumulation_steps` | Simulates larger batch size without extra memory. | 4 gives effective batch of 4 |

---

## Step 7 — Run Training

```bash
python train_lora.py --config my_lora_config.yaml
```

### What to watch for

**Good signs:**
```
Step 100: loss=0.42
Step 200: loss=0.31
Step 300: loss=0.24    ← loss decreasing = learning happening
Step 400: loss=0.19
```

**Warning signs:**
```
loss=nan               ← learning rate too high, reduce by 10x
loss stuck at 0.8+     ← not learning, check data and captions
CUDA out of memory     ← reduce lora_rank or num_frames
```

### How long it takes on RTX 3060

| Dataset size | Expected time |
|-------------|--------------|
| 20 clips, 500 steps | ~45 min |
| 50 clips, 1000 steps | ~2 hours |
| 100 clips, 2000 steps | ~4 hours |

### Checkpoints

Every `save_every_n_steps`, a `.safetensors` file is saved in `lora_output/`. Test each one in ComfyUI — training longer isn't always better. The sweet spot is usually when the subject is recognisable but the AI can still generalise.

---

## Step 8 — Use the LoRA in ComfyUI

### Add a LoRALoader node

In your workflow, add a `LoraLoader` node between `UnetLoaderGGUF` and `KSampler`:

```
[UnetLoaderGGUF] → [LoraLoader] → [KSampler]
                        ↑
               my_subject_lora.safetensors
               strength: 0.8
```

Place your LoRA file in `ComfyUI/models/loras/`.

### Updated workflow block diagram

```
[UnetLoaderGGUF]
       │
[LoraLoader] ← my_subject_lora.safetensors
       │
[KSampler]
```

### Prompt with trigger word

Include your trigger word in the positive prompt:

```
zephyr_girl laughing joyfully, bright eyes sparkling, head tilting
side to side, warm soft lighting, smooth natural motion, high detail
```

### LoRA strength tuning

| Strength | Effect |
|----------|--------|
| 0.5 | Subtle influence — maintains generality |
| 0.7–0.8 | Good balance — recognisable subject, still flexible |
| 1.0 | Strong influence — very faithful to training data |
| >1.0 | Over-fitting — may cause artefacts |

Start at 0.8 and adjust from there.

---

## Training from Images (No Video Clips)

If you only have photos, not videos, you can still train by converting image sequences to video:

### Option A — Duplicate frames (simplest)

Take a single image and repeat it as 49 identical frames. The model learns the appearance but not motion. Combine with motion captions to get the AI to animate in the style you describe.

```bash
ffmpeg -loop 1 -i your_photo.jpg -t 2 -r 25 -vf scale=768:512 clip_001.mp4
```

### Option B — Interpolated sequence (better)

If you have multiple photos of the same subject:

```bash
# Create a video that fades between photos
ffmpeg -framerate 1/2 -pattern_type glob -i '*.jpg' \
  -vf "scale=768:512,minterpolate=fps=25:mi_mode=blend" \
  -t 6 clip_001.mp4
```

### Option C — Use an image-to-video model to create training data

Use your existing workflow to generate several videos of your subject from different photos. Use those generated videos as training data. This is a bootstrapping technique that works surprisingly well.

---

## Common Problems and Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Subject not recognised | Too few training clips | Add more clips, especially varied ones |
| Face looks generic | Trigger word not in prompt | Add your trigger word to every prompt |
| Motion looks wrong | `num_frames` too low in training | Increase to 97 frames per clip |
| Training crashes (OOM) | Not enough VRAM | Reduce `lora_rank` to 16, enable gradient checkpointing |
| Loss not decreasing | Learning rate too low or bad data | Check captions, try `lr=2e-4` |
| Over-fitted (weird artefacts) | Trained too many steps | Use an earlier checkpoint |
| LoRA too strong | Strength value too high | Reduce to 0.6–0.7 |

---

## How Much Data Is Enough?

| Goal | Minimum clips | Recommended |
|------|--------------|-------------|
| Basic subject recognition | 15–20 | 40–50 |
| Consistent face/identity | 30–50 | 80–100 |
| Specific movement style | 20–30 | 50–70 |
| Scene/location | 15–20 | 30–40 |

More is better up to a point. After ~200 clips, returns diminish. Quality of captions matters as much as quantity of clips.

---

## File Checklist Before Training

```
□ Training clips collected (MP4, consistent resolution)
□ Caption .txt file for every clip
□ Trigger word in every caption
□ Safetensors model downloaded (not GGUF)
□ Training environment installed (ltxv-training repo)
□ Config file created with correct paths
□ At least 4GB free disk space for checkpoints
□ GPU confirmed visible (nvidia-smi shows it)
```

---

## What to Expect Realistically

Fine-tuning on a 12GB GPU with ~50 clips will give you:

- **Recognisable subject**: the AI will produce someone who looks like your target person
- **Not perfect identity**: it won't be a photorealistic exact replica — more like a consistent stylised version
- **Better with more data**: 100 good clips > 30 great clips
- **Motion quality unchanged**: the base model's motion quality stays the same — you're only teaching it *what* to animate, not *how*

Think of it like teaching an artist who already knows how to draw movement to draw *your* specific character consistently.
