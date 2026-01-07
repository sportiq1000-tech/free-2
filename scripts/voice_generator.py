"""
Voice Generator for The Bureaucratic Archivist
Creates natural-sounding narration with variation to avoid detection
"""

import edge_tts
import asyncio
import random
import os
from pathlib import Path

class VoiceGenerator:
    def __init__(self):
        # Male voices with deep, calm tone (good for archival content)
        self.voices = [
            'en-US-GuyNeural',           # Deep American
            'en-GB-RyanNeural',          # Warm British
            'en-AU-WilliamNeural',       # Australian
            'en-US-ChristopherNeural',   # Authoritative American
            'en-IE-ConnorNeural',        # Irish - slightly different
            'en-GB-ThomasNeural',        # British alternative
        ]
        
        # Track recently used voices to avoid repetition
        self.voice_history = []
    
    def get_varied_settings(self):
        """
        Generate randomized voice settings for each video
        This prevents YouTube's "reused content" detection
        """
        
        # Select voice NOT used in last 3 videos
        available_voices = [v for v in self.voices if v not in self.voice_history[-3:]]
        
        if not available_voices:
            available_voices = self.voices
        
        voice = random.choice(available_voices)
        
        # Track usage
        self.voice_history.append(voice)
        if len(self.voice_history) > 10:
            self.voice_history.pop(0)
        
        # Randomize parameters within "natural reading" range
        settings = {
            'voice': voice,
            'rate': f"{random.randint(-18, -8)}%",     # Slower for sleep content
            'pitch': f"{random.randint(-6, 3)}Hz",      # Slight variation
            'volume': f"{random.randint(-3, 3)}%"       # Volume variation
        }
        
        return settings
    
    async def _generate_audio_async(self, text, output_path, settings):
        """Internal async audio generation"""
        
        communicate = edge_tts.Communicate(
            text,
            settings['voice'],
            rate=settings['rate'],
            pitch=settings['pitch'],
            volume=settings['volume']
        )
        
        await communicate.save(output_path)
    
    def generate_audio(self, text, output_path, settings=None):
        """
        Generate audio file from text
        
        Args:
            text: Script text (from scriptenhancer)
            output_path: Where to save MP3
            settings: Optional voice settings (auto-generated if None)
        
        Returns:
            settings dict (for tracking what was used)
        """
        
        if settings is None:
            settings = self.get_varied_settings()
        
        print(f"\n[VOICE GENERATOR]")
        print(f"  Voice: {settings['voice']}")
        print(f"  Rate: {settings['rate']}")
        print(f"  Pitch: {settings['pitch']}")
        
        # Run async generation
        asyncio.run(self._generate_audio_async(text, output_path, settings))
        
        # Verify file was created
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✓ Audio generated: {size_mb:.2f} MB")
        else:
            print(f"  ✗ Audio generation failed")
        
        return settings
    
    def process_pause_markers(self, script_text):
        """
        Handle [Pause] markers from scriptenhancer
        
        Note: Edge-TTS doesn't support custom pauses well,
        so we'll use punctuation instead
        """
        
        # Replace pause markers with periods for natural breaks
        processed = script_text.replace('[Pause - 3 seconds]', '...')
        processed = processed.replace('[Pause - 2 seconds]', '..')
        processed = processed.replace('[Pause]', '.')
        
        return processed
    
    def generate_from_script(self, script_dict, output_path, settings=None):
        """
        Generate audio from scriptenhancer output
        
        Args:
            script_dict: Output from scriptenhancer.create_full_script()
            output_path: Where to save audio
            settings: Optional voice settings
        
        Returns:
            settings dict
        """
        
        full_script = script_dict.get('full_script', '')
        
        # Process pause markers
        processed_script = self.process_pause_markers(full_script)
        
        # Generate audio
        return self.generate_audio(processed_script, output_path, settings)


# Test function
if __name__ == "__main__":
    print("Testing voice generator...")
    
    gen = VoiceGenerator()
    
    # Test settings
    settings = gen.get_varied_settings()
    print(f"\nGenerated settings: {settings}")
    
    # Test audio generation
    test_text = """
    Welcome to the archives. Tonight, we examine a fascinating maritime log from 1887.
    The captain's entries reveal a world of wooden ships and distant horizons.
    Let us begin.
    """
    
    gen.generate_audio(test_text, "test_audio.mp3", settings)
    print("\n✓ Test complete. Check test_audio.mp3")