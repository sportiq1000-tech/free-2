"""
Video Assembler for The Bureaucratic Archivist
Creates final video using FFmpeg with Ken Burns effects
(Adapted from original video generator - keeps the good zoom logic!)
"""

import os
import subprocess
import random
import json
from pathlib import Path

class VideoAssembler:
    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path("/tmp")
    
    def get_randomized_zoom_settings(self):
        """
        Generate random Ken Burns effect settings
        (Anti-detection: each video looks different)
        """
        
        styles = ['alternate', 'zoom_in_only', 'zoom_out_only', 'pan']
        
        settings = {
            'style': random.choice(styles),
            'zoom_speed': random.uniform(0.0003, 0.0008),
            'zoom_max': random.uniform(1.15, 1.30),
            'fps': 25
        }
        
        return settings
    
    def get_audio_duration(self, audio_file):
        """Get duration of audio file in seconds"""
        
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            return float(result.stdout.strip())
        except:
            print(f"  ✗ Could not get audio duration")
            return 0
    
    def create_video_clip(self, image_path, duration, clip_index, zoom_settings):
        """
        Create a single video clip from image with zoom effect
        (This is your original FFmpeg zoom code - it's excellent!)
        """
        
        clip_path = self.temp_dir / f"clip_{clip_index:03d}.mp4"
        fps = zoom_settings['fps']
        frames = int(duration * fps)
        
        style = zoom_settings['style']
        zoom_speed = zoom_settings['zoom_speed']
        zoom_max = zoom_settings['zoom_max']
        
        # Determine zoom direction based on style
        if style == 'zoom_in_only':
            zoom_in = True
        elif style == 'zoom_out_only':
            zoom_in = False
        elif style == 'pan':
            zoom_in = None  # Pan instead
        else:  # 'alternate'
            zoom_in = (clip_index % 2 == 0)
        
        # Build zoom filter (your original logic - works great!)
        if zoom_in is None:
            # Pan effect
            zoom_filter = f"zoompan=z='1.1':x='if(lte(on,1),0,x+2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        elif zoom_in:
            # Zoom in
            zoom_filter = f"zoompan=z='min(zoom+{zoom_speed},{zoom_max})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        else:
            # Zoom out
            zoom_filter = f"zoompan=z='if(lte(zoom,1.0),{zoom_max},max(1.001,zoom-{zoom_speed}))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', str(image_path),
            '-vf', f"scale=4000:-1,{zoom_filter}",
            '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-y',
            str(clip_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and clip_path.exists():
            return str(clip_path)
        else:
            print(f"  ⚠️ Clip {clip_index} failed, using fallback...")
            
            # Fallback: simple scale without zoom
            fallback_cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', str(image_path),
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-y',
                str(clip_path)
            ]
            subprocess.run(fallback_cmd, capture_output=True)
            
            if clip_path.exists():
                return str(clip_path)
            
            return None
    
    def create_video(self, image_paths, audio_path, output_path, zoom_settings=None):
        """
        Create final video from images and audio
        
        Args:
            image_paths: List of processed image paths (from visual_generator)
            audio_path: Audio file path (from voice_generator)
            output_path: Where to save final video
            zoom_settings: Optional zoom settings (auto-generated if None)
        
        Returns:
            Path to final video
        """
        
        if zoom_settings is None:
            zoom_settings = self.get_randomized_zoom_settings()
        
        print(f"\n[VIDEO ASSEMBLER]")
        print(f"  Images: {len(image_paths)}")
        print(f"  Zoom Style: {zoom_settings['style']}")
        print(f"  Zoom Speed: {zoom_settings['zoom_speed']:.4f}")
        print(f"  Zoom Max: {zoom_settings['zoom_max']:.2f}")
        
        # Get audio duration
        duration = self.get_audio_duration(str(audio_path))
        if duration == 0:
            raise Exception("Could not determine audio duration")
        
        print(f"  Audio Duration: {duration:.1f}s")
        
        # Calculate time per image
        num_images = len(image_paths)
        time_per_image = duration / num_images
        
        print(f"  Time per image: {time_per_image:.1f}s")
        
        # Create video clips
        temp_clips = []
        
        for i, img_path in enumerate(image_paths):
            print(f"  Creating clip {i+1}/{num_images}...")
            
            clip = self.create_video_clip(
                img_path,
                time_per_image,
                i,
                zoom_settings
            )
            
            if clip:
                temp_clips.append(clip)
                print(f"    ✓ Clip {i+1} created")
            else:
                print(f"    ✗ Clip {i+1} failed")
        
        if not temp_clips:
            raise Exception("No video clips created")
        
        # Create concat file
        concat_file = self.temp_dir / "concat.txt"
        with open(concat_file, 'w') as f:
            for clip in temp_clips:
                f.write(f"file '{clip}'\n")
        
        # Merge clips with audio
        print(f"  Merging {len(temp_clips)} clips with audio...")
        
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-i', str(audio_path),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-shortest',
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Cleanup temp files
        for clip in temp_clips:
            try:
                os.remove(clip)
            except:
                pass
        
        try:
            concat_file.unlink()
        except:
            pass
        
        if result.returncode != 0:
            raise Exception(f"Video merge failed: {result.stderr}")
        
        # Verify output
        if not Path(output_path).exists():
            raise Exception("Output video not created")
        
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"  ✓ Video created: {size_mb:.1f} MB")
        
        return str(output_path)
    
    def create_single_image_video(self, image_path, audio_path, output_path, zoom_settings=None):
        """
        Simplified version for single image
        (Useful for short videos or fallback)
        """
        
        return self.create_video([image_path], audio_path, output_path, zoom_settings)


# Test
if __name__ == "__main__":
    print("Testing video assembler...")
    
    assembler = VideoAssembler()
    
    # Test settings generation
    settings = assembler.get_randomized_zoom_settings()
    print(f"\nGenerated settings: {json.dumps(settings, indent=2)}")
    
    print("\n✓ Video assembler ready")
    print("  (Actual video creation requires images + audio)")