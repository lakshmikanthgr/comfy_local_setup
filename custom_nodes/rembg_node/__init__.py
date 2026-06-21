import torch
import numpy as np
from PIL import Image


class RemoveBackground:
    MODELS = ["u2net_human_seg", "u2net", "isnet-general-use"]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (s.MODELS, {"default": "u2net_human_seg"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "remove_bg"
    CATEGORY = "image"
    TITLE = "Remove Background (rembg)"

    def remove_bg(self, image, model="u2net_human_seg"):
        from rembg import new_session, remove

        session = new_session(model)
        out_images = []
        out_masks = []

        for img_tensor in image:
            pil_img = Image.fromarray(
                (img_tensor.numpy() * 255).astype(np.uint8), mode="RGB"
            )
            # returns RGBA PIL image — background pixels have alpha=0
            result = remove(pil_img, session=session)
            result_np = np.array(result).astype(np.float32) / 255.0

            out_images.append(torch.from_numpy(result_np[:, :, :3]))
            out_masks.append(torch.from_numpy(result_np[:, :, 3]))

        return (torch.stack(out_images), torch.stack(out_masks))


NODE_CLASS_MAPPINGS = {"RemoveBackground": RemoveBackground}
NODE_DISPLAY_NAME_MAPPINGS = {"RemoveBackground": "Remove Background (rembg)"}
