"""
SDXL Lightning Engine for The Bureaucratic Archivist
Generates high-quality archival images locally on Colab GPU
Speed: ~2 seconds per image (4 steps)
"""

import torch
import os
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

# Configuration
BASE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
LIGHTNING_REPO = "ByteDance/SDXL-Lightning"
LIGHTNING_CKPT = "sdxl_lightning_4step_unet.safetensors"

# Aesthetic Suffix (The "Dark Archive" Look)
STYLE_SUFFIX = ", macro photography, dust particles, 1970s film grain, brutalist architecture, dim fluorescent lighting, 8k resolution, highly detailed texture, archival document scan, cinematic, hyperrealistic"

class SDXLEngine:
    def __init__(self):
        self.pipe = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.device == "cpu":
            print("⚠️ WARNING: No GPU detected! SDXL will be extremely slow.")
            print("   Please enable GPU in Colab: Runtime > Change runtime type > T4 GPU")

    def load_model(self):
        """Load the model into GPU memory (takes ~30s)"""
        if self.pipe is not None:
            return  # Already loaded

        print(f"⚡ Loading SDXL Lightning on {self.device.upper()}...")
        
        try:
            # 1. Load the Lightning UNet (The Speed Engine)
            unet = UNet2DConditionModel.from_config(BASE_MODEL, subfolder="unet").to(self.device, torch.float16)
            
            # Download checkpoint
            print("   Downloading Lightning weights...")
            ckpt_path = hf_hub_download(LIGHTNING_REPO, LIGHTNING_CKPT)
            unet.load_state_dict(load_file(ckpt_path, device=self.device))
            
            # 2. Load the main pipeline
            print("   Loading Base XL Pipeline...")
            self.pipe = StableDiffusionXLPipeline.from_pretrained(
                BASE_MODEL, 
                unet=unet, 
                torch_dtype=torch.float16, 
                variant="fp16"
            ).to(self.device)
            
            # 3. Set the fast scheduler
            self.pipe.scheduler = EulerDiscreteScheduler.from_config(
                self.pipe.scheduler.config, 
                timestep_spacing="trailing"
            )
            
            print("✅ SDXL Engine Ready!")
            
        except Exception as e:
            print(f"❌ Model load failed: {e}")
            raise e

    def generate_images(self, prompts, output_dir="output/sdxl_images"):
        """
        Generate a batch of images
        Args:
            prompts: List of string prompts
            output_dir: Folder to save images
        Returns:
            List of file paths
        """
        if self.pipe is None:
            self.load_model()
            
        os.makedirs(output_dir, exist_ok=True)
        generated_paths = []
        
        print(f"\n🎨 Generating {len(prompts)} images with SDXL Lightning...")
        
        for i, prompt in enumerate(prompts):
            # Add style suffix
            full_prompt = prompt + STYLE_SUFFIX
            
            print(f"   [{i+1}/{len(prompts)}] {prompt[:40]}...")
            
            # Generate (4 steps = ~2 seconds)
            # guidance_scale=0 is specific to Lightning models
            image = self.pipe(
                full_prompt, 
                num_inference_steps=4, 
                guidance_scale=0
            ).images[0]
            
            # Save
            filename = f"archivist_{i:03d}.png"
            path = os.path.join(output_dir, filename)
            image.save(path)
            generated_paths.append(path)
            
        print(f"✅ Generated {len(generated_paths)} images in {output_dir}")
        return generated_paths

    def unload_model(self):
        """Free up GPU memory"""
        if self.pipe:
            del self.pipe
            self.pipe = None
            torch.cuda.empty_cache()
            print("🗑️ SDXL Model unloaded from GPU")

# Simple test
if __name__ == "__main__":
    engine = SDXLEngine()
    engine.generate_images(["A dusty old book on a desk"])