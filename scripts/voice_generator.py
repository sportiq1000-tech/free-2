"""
Voice Generator for The Bureaucratic Archivist
Creates tired, monotone, professional narration
Optimized for sleep/relaxation content
"""

import edge_tts
import asyncio
import random

class VoiceGenerator:
    def __init__(self):
        # ONLY bureaucratic voices (tested and approved)
        self.voices = {
            'main': 'en-US-ChristopherNeural',    # Best for main content
            'intro': 'en-AU-WilliamNeural',        # Good for intros
        }
        
        # All approved voices for variety
        self.all_voices = [
            'en-US-ChristopherNeural',   # Deep, authoritative (PRIMARY)
            'en-AU-WilliamNeural',       # Calm, professional
        ]
        
        self.voice_history = []
        
        # Locked settings for bureaucratic tone
        self.bureaucratic_settings = {
            'rate_min': -22,
            'rate_max': -18,
            'pitch_min': -8,
            'pitch_max': -5,
        }
    
    def get_varied_settings(self, voice_type='main'):
        """
        Generate BUREAUCRATIC voice settings
        - Slower than normal (tired government worker)
        - Lower pitch (aged, authoritative)
        - Consistent monotone
        """
        
        # Select voice based on type
        if voice_type == 'intro':
            voice = self.voices['intro']
        else:
            voice = self.voices['main']
        
        # Generate values within bureaucratic range
        rate_val = random.randint(
            self.bureaucratic_settings['rate_min'],
            self.bureaucratic_settings['rate_max']
        )
        pitch_val = random.randint(
            self.bureaucratic_settings['pitch_min'],
            self.bureaucratic_settings['pitch_max']
        )
        volume_val = random.randint(-2, 2)
        
        # Format with proper signs (FIXED)
        rate_str = f"{rate_val}%" if rate_val < 0 else f"+{rate_val}%"
        pitch_str = f"{pitch_val}Hz" if pitch_val < 0 else f"+{pitch_val}Hz"
        volume_str = f"{volume_val}%" if volume_val < 0 else f"+{volume_val}%"
        
        settings = {
            'voice': voice,
            'rate': rate_str,
            'pitch': pitch_str,
            'volume': volume_str
        }
        
        return settings
    
    async def _generate_audio_async(self, text, output_path, settings):
        """Internal async generation"""
        
        communicate = edge_tts.Communicate(
            text,
            settings['voice'],
            rate=settings['rate'],
            pitch=settings['pitch'],
            volume=settings['volume']
        )
        
        await communicate.save(output_path)
    
    def generate_audio(self, text, output_path, settings=None):
        """Synchronous wrapper for audio generation"""
        
        if settings is None:
            settings = self.get_varied_settings()
        
        print(f"\n[VOICE GENERATOR - Bureaucratic Mode]")
        print(f"  Voice: {settings['voice']}")
        print(f"  Rate: {settings['rate']} (slow, tired)")
        print(f"  Pitch: {settings['pitch']} (deep, authoritative)")
        print(f"  Volume: {settings['volume']}")
        
        # Run async generation
        asyncio.run(self._generate_audio_async(text, output_path, settings))
        
        return settings
    
    def process_pause_markers(self, script_text):
        """
        Handle pause markers from scriptenhancer
        Add longer pauses for bureaucratic effect
        """
        
        processed = script_text.replace('[Pause - 3 seconds]', '...... ')
        processed = processed.replace('[Pause - 2 seconds]', '.... ')
        processed = processed.replace('[Pause]', '... ')
        
        return processed
    
    def generate_from_script(self, script_dict, output_path, settings=None):
        """Generate audio from scriptenhancer output"""
        
        full_script = script_dict.get('full_script', '')
        processed = self.process_pause_markers(full_script)
        
        return self.generate_audio(processed, output_path, settings)