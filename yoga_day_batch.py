"""
yoga_day_batch.py — Happy International Yoga Day batch generator

Scans a directory for images, uploads each one to ComfyUI,
and queues a video where the person says "Happy International Yoga Day!"

Usage:
    python3 yoga_day_batch.py /path/to/your/images

    # Or use current directory:
    python3 yoga_day_batch.py .

    # Custom frames (97 = ~4 sec, faster for testing):
    python3 yoga_day_batch.py /path/to/images --frames 97

Output:
    <comfyui-install>/output/video/yoga_day/
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

COMFYUI_URL   = "http://localhost:8189"
WORKFLOW_FILE = str(Path(__file__).parent / "workflows/ltxv_096_gguf_i2v.json")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# Prompt: person is joyfully saying "Happy International Yoga Day!"
# Describes mouth movement, gesture, and festive expression.
POSITIVE_PROMPT = (
    "person joyfully speaking and announcing, mouth open mid-speech, "
    "saying Happy International Yoga Day, bright warm smile, "
    "hands pressed together in namaste prayer gesture at chest, "
    "eyes sparkling with joy and celebration, head nodding slightly, "
    "festive cheerful energy, smooth natural motion, "
    "cinematic quality, high detail, warm golden lighting"
)

NEGATIVE_PROMPT = (
    "worst quality, low quality, blurry, jittery, flickering, "
    "distorted face, deformed features, unnatural motion, "
    "inconsistent motion, choppy, artifacts, static, frozen, "
    "lifeless expression, multiple faces, bad hands"
)

# Node IDs in ltxv_096_gguf_i2v.json
NODE_IMAGE    = 4
NODE_POSITIVE = 5
NODE_NEGATIVE = 6
NODE_IMGVIDEO = 8
NODE_SAMPLER  = 9
NODE_SAVE     = 12

# Video settings
WIDTH   = 768
HEIGHT  = 512
STEPS   = 8
CFG     = 1.0
SEED    = 42    # fixed seed for reproducibility; change per run for variation

# ── HELPERS ───────────────────────────────────────────────────────────────────

WIDGET_NAMES = {
    "UnetLoaderGGUF":   ["unet_name"],
    "ClipLoaderGGUF":   ["clip_name", "type"],
    "VaeGGUF":          ["vae_name"],
    "LoadImage":        ["image"],
    "CLIPTextEncode":   ["text"],
    "LTXVConditioning": ["frame_rate"],
    "LTXVImgToVideo":   ["width", "height", "length", "batch_size", "strength"],
    "KSampler":         ["seed", "control_after_generate", "steps", "cfg",
                         "sampler_name", "scheduler", "denoise"],
    "VAEDecode":        [],
    "CreateVideo":      ["fps"],
    "SaveVideo":        ["filename_prefix", "format", "codec"],
}


def comfyui_online():
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=4)
        return True
    except Exception:
        return False


def upload_image(image_path: Path) -> str:
    """Upload an image to ComfyUI's input folder. Returns the stored filename."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    boundary = "----ComfyUIBoundary"
    content_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + image_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    return result["name"]


def build_base_prompt(workflow: dict) -> dict:
    link_map = {}
    for link in workflow["links"]:
        link_map[link[0]] = [str(link[1]), link[2]]

    prompt = {}
    for node in workflow["nodes"]:
        nid = str(node["id"])
        inputs = {}
        for inp in node.get("inputs", []):
            if inp.get("link") is not None and inp["link"] in link_map:
                inputs[inp["name"]] = link_map[inp["link"]]
        wnames = WIDGET_NAMES.get(node["type"], [])
        for i, val in enumerate(node.get("widgets_values", [])):
            if i < len(wnames):
                inputs[wnames[i]] = val
        prompt[nid] = {"class_type": node["type"], "inputs": inputs}
    return prompt


def patch_prompt(base: dict, uploaded_filename: str, frames: int, seed: int) -> dict:
    import copy
    p = copy.deepcopy(base)

    p[str(NODE_IMAGE)]["inputs"]["image"]    = uploaded_filename
    p[str(NODE_POSITIVE)]["inputs"]["text"]  = POSITIVE_PROMPT
    p[str(NODE_NEGATIVE)]["inputs"]["text"]  = NEGATIVE_PROMPT

    iv = p[str(NODE_IMGVIDEO)]["inputs"]
    iv["width"]  = WIDTH
    iv["height"] = HEIGHT
    iv["length"] = frames

    s = p[str(NODE_SAMPLER)]["inputs"]
    s["seed"]                   = seed
    s["control_after_generate"] = "fixed"
    s["steps"]                  = STEPS
    s["cfg"]                    = CFG

    # Save into a yoga_day subfolder
    p[str(NODE_SAVE)]["inputs"]["filename_prefix"] = "video/yoga_day"

    return p


def queue_prompt(prompt: dict) -> str:
    payload = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read()).get("prompt_id", "?")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate 'Happy International Yoga Day!' videos from a folder of images."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Directory containing input images (default: current directory)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=249,
        help="Number of frames: 97=~4s, 177=~7s, 249=~10s (default: 249)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Random seed (default: {SEED})",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        print(f"ERROR: '{input_dir}' is not a directory.")
        sys.exit(1)

    images = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        print(f"No images found in {input_dir}")
        print(f"Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
        sys.exit(1)

    print(f"\n  Happy International Yoga Day! — Batch Generator")
    print(f"  ------------------------------------------------")
    print(f"  Input folder : {input_dir}")
    print(f"  Images found : {len(images)}")
    print(f"  Frames       : {args.frames} (~{args.frames / 25:.0f} seconds)")
    print(f"  Resolution   : {WIDTH}x{HEIGHT}")
    print(f"  Seed         : {args.seed}")
    print(f"  Output       : <comfyui>/output/video/yoga_day/")
    print()

    if not comfyui_online():
        print(f"ERROR: ComfyUI not reachable at {COMFYUI_URL}")
        print("Start it: cd <install-dir> && source venv/bin/activate && python main.py --listen")
        sys.exit(1)

    with open(WORKFLOW_FILE) as f:
        workflow = json.load(f)
    base_prompt = build_base_prompt(workflow)

    queued = []
    failed = []

    for i, image_path in enumerate(images, 1):
        print(f"  [{i:2d}/{len(images)}] {image_path.name}", end="  ", flush=True)

        try:
            uploaded_name = upload_image(image_path)
            print(f"uploaded → {uploaded_name}", end="  ", flush=True)

            prompt = patch_prompt(base_prompt, uploaded_name, args.frames, args.seed + i - 1)
            pid = queue_prompt(prompt)
            print(f"queued  id={pid}")
            queued.append((image_path.name, pid))

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"FAILED  HTTP {e.code}: {body[:200]}")
            failed.append(image_path.name)
        except Exception as e:
            print(f"FAILED  {e}")
            failed.append(image_path.name)

        if i < len(images):
            time.sleep(0.3)

    print()
    print(f"  Done — {len(queued)} queued, {len(failed)} failed")
    if queued:
        mins_per_video = args.frames / 249 * 22   # rough estimate
        total_mins = len(queued) * mins_per_video
        print(f"  Estimated time : ~{total_mins:.0f} min ({total_mins/60:.1f} hours)")
        print(f"  Watch progress : {COMFYUI_URL}")
        print()

    if failed:
        print(f"  Failed images:")
        for name in failed:
            print(f"    - {name}")
        print()

    if queued:
        print(f"  Queued prompt IDs:")
        for name, pid in queued:
            print(f"    {name:30s}  {pid}")
        print()


if __name__ == "__main__":
    main()
