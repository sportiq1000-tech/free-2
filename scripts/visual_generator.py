"""
Visual Generator for The Bureaucratic Archivist
Creates aged, archival-style visuals from document images
"""

import os
import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import requests
from io import BytesIO

class VisualGenerator:
    def __init__(self, assets_dir="assets"):
        self.assets_dir = assets_dir
        
        # Create assets directory if needed
        os.makedirs(assets_dir, exist_ok=True)
    
    def download_image(self, url, output_path):
        """Download image from URL"""
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img.save(output_path)
                return output_path
            return None
        except Exception as e:
            print(f"  Download error: {e}")
            return None
    
    def apply_archival_effect(self, input_path, output_path):
        """
        Apply dark, aged, archival effect to image
        
        This creates the "Bureaucratic Archivist" aesthetic:
        - Desaturated / sepia tones
        - Aged paper look
        - Subtle grain and vignette
        - Darkened for sleep-friendly viewing
        """
        
        img = Image.open(input_path).convert('RGB')
        
        # Randomized parameters (avoid identical processing)
        brightness = random.uniform(0.5, 0.7)
        saturation = random.uniform(0.25, 0.40)
        contrast = random.uniform(0.80, 0.95)
        sepia_strength = random.uniform(0.65, 0.85)
        grain_amount = random.uniform(4, 10)
        
        print(f"\n[VISUAL GENERATOR]")
        print(f"  Brightness: {brightness:.2f}")
        print(f"  Saturation: {saturation:.2f}")
        print(f"  Sepia: {sepia_strength:.2f}")
        
        # Apply adjustments
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Color(img).enhance(saturation)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        
        # Sepia tone effect
        arr = np.array(img, dtype=np.float32)
        
        sepia_matrix = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131]
        ])
        
        sepia_arr = arr @ sepia_matrix.T
        arr = arr * (1 - sepia_strength) + sepia_arr * sepia_strength
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        
        img = Image.fromarray(arr)
        
        # Add film grain
        grain = np.random.normal(0, grain_amount, arr.shape)
        arr = np.clip(arr.astype(np.float32) + grain, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
        
        # Slight blur (vintage lens effect)
        blur_radius = random.uniform(0.3, 0.7)
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Add vignette
        img = self._add_vignette(img, strength=random.uniform(0.35, 0.55))
        
        # Save
        img.save(output_path, quality=92)
        print(f"  ✓ Archival effect applied: {output_path}")
        
        return output_path
    
    def _add_vignette(self, img, strength=0.5):
        """Add dark vignette effect to edges"""
        
        arr = np.array(img, dtype=np.float32)
        rows, cols = arr.shape[:2]
        
        # Create radial gradient mask
        X = np.arange(0, cols)
        Y = np.arange(0, rows)
        X, Y = np.meshgrid(X, Y)
        
        centerX = cols / 2
        centerY = rows / 2
        
        # Distance from center
        mask = np.sqrt((X - centerX)**2 + (Y - centerY)**2)
        mask = mask / mask.max()
        
        # Apply vignette
        mask = 1 - (mask * strength)
        
        for i in range(3):
            arr[:, :, i] = arr[:, :, i] * mask
        
        return Image.fromarray(arr.astype(np.uint8))
    
    def create_paper_background(self, output_path, size=(1920, 1080)):
        """
        Create aged paper texture background
        (Used if no document images available)
        """
        
        # Start with off-white paper color
        base_color = (235, 225, 210)
        img = Image.new('RGB', size, color=base_color)
        arr = np.array(img, dtype=np.float32)
        
        # Add paper texture noise
        noise = np.random.normal(0, 8, arr.shape)
        arr = np.clip(arr + noise, 0, 255)
        
        # Add random stains/spots
        for _ in range(random.randint(4, 8)):
            x = random.randint(0, size[0])
            y = random.randint(0, size[1])
            radius = random.randint(60, 250)
            
            # Create circular stain
            for i in range(max(0, y-radius), min(size[1], y+radius)):
                for j in range(max(0, x-radius), min(size[0], x+radius)):
                    dist = ((i-y)**2 + (j-x)**2) ** 0.5
                    if dist < radius:
                        factor = 1 - (dist / radius) * random.uniform(0.2, 0.4)
                        arr[i, j] = arr[i, j] * factor
        
        img = Image.fromarray(arr.astype(np.uint8))
        img.save(output_path, quality=90)
        
        return output_path
    
    def generate_thumbnail(self, title, year, output_path, style='dark'):
        """
        Generate YouTube thumbnail (1280x720)
        
        Args:
            title: Video title
            year: Document year
            output_path: Where to save
            style: 'dark' or 'light'
        """
        
        # Create base
        if style == 'dark':
            bg_color = (20, 18, 15)
            text_color = (210, 195, 170)
            border_color = (80, 70, 55)
        else:
            bg_color = (235, 225, 210)
            text_color = (50, 40, 30)
            border_color = (120, 100, 80)
        
        img = Image.new('RGB', (1280, 720), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add decorative borders
        draw.rectangle([30, 30, 1250, 690], outline=border_color, width=4)
        draw.rectangle([50, 50, 1230, 670], outline=border_color, width=2)
        
        # Try to load a serif font (fallback to default if not available)
        try:
            # Common font locations
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                "C:\\Windows\\Fonts\\georgiab.ttf"
            ]
            
            title_font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    title_font = ImageFont.truetype(font_path, 56)
                    year_font = ImageFont.truetype(font_path, 38)
                    break
            
            if title_font is None:
                title_font = ImageFont.load_default()
                year_font = ImageFont.load_default()
                
        except:
            title_font = ImageFont.load_default()
            year_font = ImageFont.load_default()
        
        # Wrap title text
        title_short = title[:55] + "..." if len(title) > 55 else title
        
        # Draw text (centered)
        draw.text((640, 280), title_short, font=title_font, fill=text_color, anchor="mm")
        draw.text((640, 400), f"— {year} —", font=year_font, fill=text_color, anchor="mm")
        
        # Add "ARCHIVE" stamp
        stamp_color = (100, 40, 40) if style == 'dark' else (150, 60, 60)
        draw.text((640, 550), "◆ HISTORICAL ARCHIVE ◆", font=year_font, fill=stamp_color, anchor="mm")
        
        # Add subtle texture
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, 5, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
        
        img.save(output_path, quality=95)
        print(f"  ✓ Thumbnail created: {output_path}")
        
        return output_path
    
    def process_document_images(self, image_urls, output_dir, max_images=10):
        """
        Download and process multiple document images
        (Works with output from document_scraper)
        
        Args:
            image_urls: List of image URLs from document_scraper
            output_dir: Where to save processed images
            max_images: Maximum images to process
        
        Returns:
            List of processed image paths
        """
        
        os.makedirs(output_dir, exist_ok=True)
        
        processed_images = []
        
        for i, url in enumerate(image_urls[:max_images]):
            print(f"\n  Processing image {i+1}/{min(len(image_urls), max_images)}")
            
            # Download
            raw_path = os.path.join(output_dir, f"raw_{i:02d}.jpg")
            downloaded = self.download_image(url, raw_path)
            
            if downloaded:
                # Apply archival effect
                processed_path = os.path.join(output_dir, f"processed_{i:02d}.jpg")
                self.apply_archival_effect(raw_path, processed_path)
                processed_images.append(processed_path)
        
        print(f"\n  ✓ Processed {len(processed_images)} images")
        
        return processed_images


# Test
if __name__ == "__main__":
    print("Testing visual generator...")
    
    gen = VisualGenerator()
    
    # Create test paper background
    gen.create_paper_background("test_paper.jpg")
    print("✓ Created test_paper.jpg")
    
    # Apply archival effect
    gen.apply_archival_effect("test_paper.jpg", "test_archival.jpg")
    print("✓ Created test_archival.jpg")
    
    # Create thumbnail
    gen.generate_thumbnail(
        "Maritime Log from the SS Enterprise",
        "1887",
        "test_thumbnail.jpg"
    )
    print("✓ Created test_thumbnail.jpg")