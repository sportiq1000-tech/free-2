"""
Voice Generator for The Bureaucratic Archivist
Creates tired, monotone, professional narration
"""

import edge_tts
import asyncio
import random

class VoiceGenerator:
    def __init__(self):
        # ONLY use deep, calm, "tired professional" voices
        self.voices = [
            'en-GB-RyanNeural',          # British, professional (BEST)
            'en-US-GuyNeural',           # American, flat
            'en-AU-WilliamNeural',       # Australian, calm
            'en-US-ChristopherNeural',   # American, deep
        ]
        
        # Remove upbeat voices:
        # ❌ en-IE-ConnorNeural (too cheerful)
        # ❌ en-GB-ThomasNeural (too young)
        
        self.voice_history = []
    
    def get_varied_settings(self):
        """
        Generate BUREAUCRATIC voice settings
        - Slower than normal (tired)
        - Lower pitch (aged, authoritative)
        - Consistent monotone
        """
        
        # Select voice not used recently
        available = [v for v in self.voices if v not in self.voice_history[-2:]]
        voice = random.choice(available) if available else random.choice(self.voices)
        
        # Track usage
        self.voice_history.append(voice)
        if len(self.voice_history) > 10:
            self.voice_history.pop(0)
        
        # BUREAUCRATIC settings (slower, deeper, flatter)
        rate_val = random.randint(-25, -18)      # Much slower (was -18 to -8)
        pitch_val = random.randint(-8, -3)        # Deeper (was -6 to +3)
        volume_val = random.randint(-2, 2)
        
        settings = {
            'voice': voice,
            'rate': f"{rate_val}%",
            'pitch': f"{pitch_val}Hz",
            'volume': f"+{volume_val}%" if volume_val >= 0 else f"{volume_val}%"
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
        """Synchronous wrapper"""
        
        if settings is None:
            settings = self.get_varied_settings()
        
        print(f"\n[VOICE GENERATOR - Bureaucratic Mode]")
        print(f"  Voice: {settings['voice']}")
        print(f"  Rate: {settings['rate']} (slow, tired)")
        print(f"  Pitch: {settings['pitch']} (deep, authoritative)")
        
        asyncio.run(self._generate_audio_async(text, output_path, settings))
        
        return settings
    
    def process_pause_markers(self, script_text):
        """Handle pause markers from script"""
        
        # Add longer pauses for bureaucratic effect
        processed = script_text.replace('[Pause - 3 seconds]', '...... ')
        processed = processed.replace('[Pause - 2 seconds]', '.... ')
        processed = processed.replace('[Pause]', '... ')
        
        return processed
    
    def generate_from_script(self, script_dict, output_path, settings=None):
        """Generate audio from script data"""
        
        full_script = script_dict.get('full_script', '')
        processed = self.process_pause_markers(full_script)
        
        return self.generate_audio(processed, output_path, settings)