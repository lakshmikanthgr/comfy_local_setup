FROM comfyui-nodes:latest

WORKDIR /app/ComfyUI

# Copy workflows into image so they appear in the browser immediately
COPY workflows/ user/default/workflows/

# Copy our custom nodes (rembg_node for background removal)
COPY custom_nodes/ custom_nodes/

# Model directories are volume-mounted at runtime — create empty placeholders
RUN mkdir -p models/unet models/clip models/vae models/checkpoints \
             output input temp

EXPOSE 8188

# --listen enables connections from outside the container
# --preview-method auto picks the best latent preview method available
ENTRYPOINT ["python3", "main.py", "--listen", "--port", "8188", "--preview-method", "auto"]
