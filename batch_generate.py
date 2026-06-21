"""
Batch video generator for ltxv_096_gguf_scene_character workflow.

Queues multiple (scene × prompt × seed) combinations automatically.
Each combination becomes one video in ComfyUI's output folder.

Usage:
    python3 batch_generate.py

Edit the CONFIG section below before running.
Images must already exist in ComfyUI's input/ directory.
"""

import json
import urllib.request
import urllib.error
import time
from pathlib import Path
from itertools import product

# ── CONFIG ────────────────────────────────────────────────────────────────────

COMFYUI_URL    = "http://localhost:8189"
WORKFLOW_FILE  = "/home/laks/projects/comfy_local_setup/workflows/ltxv_096_gguf_scene_character.json"
CHARACTER_IMAGE = "janasenani_1.jpg"   # filename in ComfyUI input/ folder

# One video is generated for every (scene, prompt, seed) combination.
# 3 scenes × 2 prompts × 2 seeds = 12 videos queued in one run.

SCENES = [
    "scene_bg.png",
    # "forest_bg.png",
    # "beach_bg.png",
]

POSITIVE_PROMPTS = [
    (
        "A cheerful girl laughing with pure joy, bright eyes sparkling, "
        "wide natural smile, head tilting side to side playfully, shoulders bouncing, "
        "warm golden afternoon light, smooth natural motion, cinematic quality, high detail"
    ),
    # (
    #     "A happy girl waving hello enthusiastically, arm raised and waving, "
    #     "big warm smile, joyful expression, soft natural lighting, "
    #     "smooth natural motion, cinematic quality, high detail"
    # ),
]

NEGATIVE_PROMPT = (
    "worst quality, low quality, blurry, jittery, flickering, distorted face, "
    "deformed features, unnatural motion, inconsistent motion, choppy, artifacts, "
    "overexposed, dark, dull colors, static, frozen, lifeless expression, "
    "morphing face, multiple faces, bad compositing, visible seams"
)

SEEDS = [42, 123]   # add more seeds for more variation per prompt

# Video settings — change if needed
WIDTH   = 768
HEIGHT  = 512
FRAMES  = 249   # 8n+1: 97 (~4s), 177 (~7s), 201 (~8s), 225 (~9s), 249 (~10s)
STEPS   = 8
CFG     = 1.0

# ── NODE IDs (match the workflow JSON) ────────────────────────────────────────

NODE_CHARACTER  = 4     # LoadImage — character
NODE_SCENE      = 13    # LoadImage — scene background
NODE_POSITIVE   = 5     # CLIPTextEncode — positive prompt
NODE_NEGATIVE   = 6     # CLIPTextEncode — negative prompt
NODE_IMGVIDEO   = 8     # LTXVImgToVideo — width, height, length, batch_size, strength
NODE_SAMPLER    = 9     # KSampler — seed, control_after_generate, steps, cfg, ...

# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_workflow():
    with open(WORKFLOW_FILE) as f:
        return json.load(f)

def build_link_map(workflow):
    link_map = {}
    for link in workflow["links"]:
        link_id, from_node, from_slot = link[0], link[1], link[2]
        link_map[link_id] = [str(from_node), from_slot]
    return link_map

WIDGET_NAMES = {
    "UnetLoaderGGUF":        ["unet_name"],
    "ClipLoaderGGUF":        ["clip_name", "type"],
    "VaeGGUF":               ["vae_name"],
    "LoadImage":             ["image"],
    "RemoveBackgroundRembg": ["model"],
    "ImageScale":            ["upscale_method", "width", "height", "crop"],
    "ImageCompositeMasked":  ["x", "y", "resize_source"],
    "CLIPTextEncode":        ["text"],
    "LTXVConditioning":      ["frame_rate"],
    "LTXVImgToVideo":        ["width", "height", "length", "batch_size", "strength"],
    "KSampler":              ["seed", "control_after_generate", "steps", "cfg",
                              "sampler_name", "scheduler", "denoise"],
    "VAEDecode":             [],
    "CreateVideo":           ["fps"],
    "SaveVideo":             ["filename_prefix", "format", "codec"],
}

def build_base_prompt(workflow):
    link_map = build_link_map(workflow)
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

def patch_prompt(prompt, character, scene, positive, negative, seed):
    """Return a copy of prompt with this run's values applied."""
    import copy
    p = copy.deepcopy(prompt)

    p[str(NODE_CHARACTER)]["inputs"]["image"]  = character
    p[str(NODE_SCENE)]["inputs"]["image"]       = scene
    p[str(NODE_POSITIVE)]["inputs"]["text"]     = positive
    p[str(NODE_NEGATIVE)]["inputs"]["text"]     = negative

    sampler = p[str(NODE_SAMPLER)]["inputs"]
    sampler["seed"]                    = seed
    sampler["control_after_generate"]  = "fixed"
    sampler["steps"]                   = STEPS
    sampler["cfg"]                     = CFG

    iv = p[str(NODE_IMGVIDEO)]["inputs"]
    iv["width"]  = WIDTH
    iv["height"] = HEIGHT
    iv["length"] = FRAMES

    return p

def queue_prompt(prompt):
    payload = json.dumps({"prompt": prompt}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def comfyui_online():
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=3)
        return True
    except Exception:
        return False

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not comfyui_online():
        print(f"ERROR: ComfyUI not reachable at {COMFYUI_URL}")
        print("Start it first: cd <install-dir> && source venv/bin/activate && python main.py --listen")
        return

    workflow   = load_workflow()
    base_prompt = build_base_prompt(workflow)

    combos = list(product(SCENES, POSITIVE_PROMPTS, SEEDS))
    print(f"Queueing {len(combos)} videos  ({len(SCENES)} scenes × {len(POSITIVE_PROMPTS)} prompts × {len(SEEDS)} seeds)")
    print(f"Character: {CHARACTER_IMAGE}  |  {WIDTH}×{HEIGHT}  {FRAMES} frames  {STEPS} steps")
    print()

    queued = []
    for i, (scene, positive, seed) in enumerate(combos, 1):
        prompt = patch_prompt(base_prompt, CHARACTER_IMAGE, scene, positive, NEGATIVE_PROMPT, seed)
        try:
            result = queue_prompt(prompt)
            pid = result.get("prompt_id", "?")
            queued.append(pid)
            print(f"  [{i:2d}/{len(combos)}] queued  scene={scene}  seed={seed}  id={pid}")
            if i < len(combos):
                time.sleep(0.3)   # avoid hammering the API
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  [{i:2d}/{len(combos)}] FAILED  scene={scene}  seed={seed}")
            print(f"           HTTP {e.code}: {body[:300]}")

    print()
    print(f"Done. {len(queued)}/{len(combos)} jobs queued.")
    print(f"Watch: {COMFYUI_URL}")
    print(f"Output: <install-dir>/output/video/ltxv_scene_character/")
    print()
    print("Prompt IDs:")
    for pid in queued:
        print(f"  {pid}")

if __name__ == "__main__":
    main()
