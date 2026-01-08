"""
Auto-Visuals for The Bureaucratic Archivist
1. Reads the script text
2. Generates prompts using Groq
3. Generates high-quality images using local SDXL Lightning
"""

import os
import requests
import json
import random
import time
from sdxl_engine import SDXLEngine

# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

def generate_prompts_from_script(script_text, count=10):
    """
    Ask Groq to invent image prompts based on the video topic.
    """
    print(f"  🧠 Brainstorming {count} image prompts...")
    
    # Take a sample of the script to understand context
    sample = script_text[:3000]
    
    prompt = f"""You are an Art Director for a historical documentary.
    
    VIDEO SCRIPT SAMPLE:
    "{sample}..."
    
    TASK: Write {count} visual image prompts to match this mood.
    
    THEME: "The Bureaucratic Archivist". 
    SUBJECTS: Old paper, ink bottles, dusty archives, specific objects mentioned in text, government buildings, typewriter keys, wax seals.
    
    CONSTRAINT: Return ONLY a JSON list of strings. No other text.
    
    Example: ["Close up of a fountain pen on yellowed paper", "Dimly lit library aisle"]
    """
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        
        content = response.json()["choices"][0]["message"]["content"]
        
        # Extract list from potential extra text
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            prompts = json.loads(match.group())
            return prompts[:count] # Ensure exact count
            
    except Exception as e:
        print(f"  ❌ Prompt generation failed: {e}")
        
    # Fallback prompts if AI fails
    return [
        "Dusty leather bound book on oak desk",
        "Vintage typewriter keys close up",
        "Stack of yellowed government papers",
        "Dimly lit archive room with dust motes",
        "Close up of handwritten ink script",
        "Antique magnifying glass on map",
        "Row of wooden filing cabinets",
        "Old wax seal on envelope",
        "Faded black and white photograph of building",
        "Texture of crinkled parchment paper"
    ]

def create_auto_images(script_text, count=10, output_dir="output/auto_images"):
    """
    Main Orchestrator
    """
    # 1. Get Prompts
    prompts = generate_prompts_from_script(script_text, count)
    print(f"  📋 Generated {len(prompts)} prompts.")
    
    # 2. Generate Images with SDXL
    engine = SDXLEngine()
    
    try:
        generated_files = engine.generate_images(prompts, output_dir)
        
        # Unload to save memory for FFmpeg later
        engine.unload_model()
        
        return generated_files
        
    except Exception as e:
        print(f"  ❌ SDXL Generation failed: {e}")
        return []