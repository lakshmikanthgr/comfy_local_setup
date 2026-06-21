import json, urllib.request, sys

COMFYUI_URL = "http://localhost:8189"
WORKFLOW_FILE = "/home/laks/projects/comfy_local_setup/workflows/ltxv_096_gguf_scene_character.json"
CHARACTER_IMAGE = "janasenani_1.jpg"
SCENE_IMAGE     = "scene_bg.png"

with open(WORKFLOW_FILE) as f:
    workflow = json.load(f)

# Patch image filenames into the two LoadImage nodes
for node in workflow["nodes"]:
    if node["id"] == 4:   # Character LoadImage
        node["widgets_values"][0] = CHARACTER_IMAGE
    if node["id"] == 13:  # Scene LoadImage
        node["widgets_values"][0] = SCENE_IMAGE

# Build link map: link_id → [from_node_id_str, from_slot]
link_map = {}
for link in workflow["links"]:
    link_id, from_node, from_slot = link[0], link[1], link[2]
    link_map[link_id] = [str(from_node), from_slot]

# Widget name ordering per node type
WIDGET_NAMES = {
    "UnetLoaderGGUF":       ["unet_name"],
    "ClipLoaderGGUF":       ["clip_name", "type"],
    "VaeGGUF":              ["vae_name"],
    "LoadImage":            ["image"],
    "RemoveBackgroundRembg": ["model"],
    "ImageScale":           ["upscale_method", "width", "height", "crop"],
    "ImageCompositeMasked": ["x", "y", "resize_source"],
    "CLIPTextEncode":       ["text"],
    "LTXVConditioning":     ["frame_rate"],
    "LTXVImgToVideo":       ["width", "height", "length", "batch_size", "strength"],
    "KSampler":             ["seed", "control_after_generate", "steps", "cfg",
                             "sampler_name", "scheduler", "denoise"],
    "VAEDecode":            [],
    "CreateVideo":          ["fps"],
    "SaveVideo":            ["filename_prefix", "format", "codec"],
}

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

# Debug: print the built inputs for key nodes
for nid in ["14", "15", "16", "8"]:
    if nid in prompt:
        print(f"\nNode {nid} ({prompt[nid]['class_type']}):")
        print(json.dumps(prompt[nid]["inputs"], indent=2))

payload = json.dumps({"prompt": prompt}).encode()
req = urllib.request.Request(
    f"{COMFYUI_URL}/prompt",
    data=payload,
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2))
    print(f"\nQueued! Prompt ID: {result.get('prompt_id')}")
    print(f"Watch progress at: {COMFYUI_URL}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
