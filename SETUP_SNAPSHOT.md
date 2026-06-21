# ComfyUI Setup Snapshot

Frozen setup for LTX-Video 0.9.6 GGUF image-to-video on RTX 3060 12GB.

## ComfyUI Core

| Repo | Commit |
|------|--------|
| https://github.com/comfyanonymous/ComfyUI.git | `0d8b7510bdc5409f4a76c3191e122ddea50f4aa2` |

## Custom Nodes

| Name | Repo | Commit |
|------|------|--------|
| ComfyUI-GGUF | https://github.com/city96/ComfyUI-GGUF.git | `6ea2651e7df66d7585f6ffee804b20e92fb38b8a` |
| ComfyUI-LTXVideo | https://github.com/Lightricks/ComfyUI-LTXVideo.git | `4f45fd6c222eb06eb3e46605da62e7c889e4be5c` |
| calcuis-gguf | https://github.com/calcuis/gguf.git | `2902c546c18231e4323fa2c0d63455c34ed79e5a` |
| ComfyUI-Manager | https://github.com/ltdrdata/ComfyUI-Manager.git | `8d5c12037f873c2f9e059e4f9c409a2835a9b8cf` |
| ComfyUI-VideoHelperSuite | https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite | `2984ec4c4b93292421888f38db74a5e8802a8ff8` |
| ComfyUI-WanVideoWrapper | https://github.com/Kijai/ComfyUI-WanVideoWrapper.git | `df8f3e49daaad117cf3090cc916c83f3d001494c` |
| ComfyUI-Florence2 | https://github.com/kijai/ComfyUI-Florence2.git | `9ece3de914214c5f581d725167bc9d0eeb0d1120` |

## Python Packages (key)

```
torch==2.5.1+cu121
torchvision==0.20.1+cu121
torchaudio==2.5.1+cu121
transformers==5.7.0
diffusers==0.38.0
safetensors==0.8.0rc0
accelerate==1.13.0
numpy==2.2.6
gguf==0.18.0
gguf-connector==3.5.4
torchsde==0.2.6
```

## Models Required

Place in the corresponding `models/` subdirectory:

| File | Directory | Source |
|------|-----------|--------|
| `ltxv-2b-0.9.6-distilled-q6_k.gguf` | `models/unet/` | Hugging Face — calcuis/ltxv-2b-0.9.6-gguf |
| `t5xxl_fp32-q4_0.gguf` | `models/clip/` | Hugging Face — calcuis/t5xxl-gguf or similar |
| `pig_video_enhanced_vae_fp32-f16.gguf` | `models/vae/` | Hugging Face — calcuis ecosystem |

## Workflow

`user/default/workflows/ltxv_096_gguf_i2v.json`

Node pipeline:
```
UnetLoaderGGUF (city96)
ClipLoaderGGUF (calcuis) — type: ltxv
VaeGGUF        (calcuis)
LoadImage
CLIPTextEncode x2 → LTXVConditioning (frame_rate=25)
LTXVImgToVideo (768×512, 249 frames ~10sec, strength=1.0)
KSampler       (seed=42, steps=8, cfg=1.0, euler, sgm_uniform, denoise=1.0)
VAEDecode → CreateVideo (25fps) → SaveVideo
```

## Notes

- `ClipLoaderGGUF` (calcuis, lowercase l) must be used — city96's `CLIPLoaderGGUF` errors on non-llama.cpp GGUF files
- `VaeGGUF` is from calcuis-gguf only — standard VAELoader cannot load `.gguf` VAE files
- LTX-Video frame constraint: length must be `8n+1` (e.g. 97, 177, 201, 225, 249)
- Distilled model settings: steps=8, cfg=1.0, euler sampler, sgm_uniform scheduler
