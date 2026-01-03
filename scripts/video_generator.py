import os
import asyncio
import json
import requests
import subprocess
from pathlib import Path

# Configuration from environment variables
SCRIPT_TEXT = os.environ.get('SCRIPT_TEXT', 'Welcome to this history video.')
IMAGE_URLS = os.environ.get('IMAGE_URLS', '').split(',')
VIDEO_TITLE = os.environ.get('VIDEO_TITLE', 'History Video')
JOB_ID = os.environ.get('JOB_ID', 'unknown')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')
RCLONE_TOKEN = os.environ.get('RCLONE_TOKEN', '')

# ============================================
# VOICE SETTINGS - Customize here!
# ============================================
# Available voices:
# - en-US-DavisNeural (deep, calm male) ⭐ RECOMMENDED
# - en-US-GuyNeural (neutral male)
# - en-US-TonyNeural (warm male)
# - en-GB-RyanNeural (British male)
# - en-US-JennyNeural (calm female)
# - en-AU-WilliamNeural (Australian male)

VOICE = os.environ.get('VOICE', 'en-US-ChristopherNeural')

# Rate: -20% to +20% (negative = slower)
# Recommended: -5% to -10% for calm content
RATE = os.environ.get('RATE', '-8%')

# Pitch: -10Hz to +10Hz (negative = deeper)
# Recommended: -2Hz to +0Hz for calm content
PITCH = os.environ.get('PITCH', '-2Hz')

# ============================================
# ZOOM/PAN SETTINGS - Customize here!
# ============================================
# Zoom speed: 0.0003 (very slow) to 0.002 (fast)
ZOOM_SPEED = float(os.environ.get('ZOOM_SPEED', '0.0005'))

# Zoom range: 1.1 (subtle) to 1.5 (dramatic)
ZOOM_MAX = float(os.environ.get('ZOOM_MAX', '1.25'))

# Effect style: 'alternate', 'zoom_in_only', 'zoom_out_only', 'pan'
ZOOM_STYLE = os.environ.get('ZOOM_STYLE', 'alternate')


def download_images(urls, output_dir="images"):
    """Download images from direct URLs"""
    Path(output_dir).mkdir(exist_ok=True)
    downloaded = []
    
    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue
        
        try:
            print(f"  Downloading image {i+1}: {url[:70]}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=120)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                ext = 'png' if 'png' in content_type else 'jpg'
                
                filepath = f"{output_dir}/image_{i:03d}.{ext}"
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                file_size = os.path.getsize(filepath)
                if file_size > 5000:
                    downloaded.append(filepath)
                    print(f"    ✓ Saved: {filepath} ({file_size // 1024}KB)")
                else:
                    os.remove(filepath)
                    print(f"    ✗ Too small, skipped")
            else:
                print(f"    ✗ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    if not downloaded:
        print("  Creating placeholder image...")
        placeholder = f"{output_dir}/image_000.jpg"
        cmd = [
            'ffmpeg', '-f', 'lavfi', 
            '-i', 'color=c=0x1a1a2e:s=1920x1080:d=1',
            '-frames:v', '1', 
            '-y', placeholder
        ]
        subprocess.run(cmd, capture_output=True)
        if os.path.exists(placeholder):
            downloaded.append(placeholder)
    
    return downloaded


async def generate_audio(text, output_file="audio.mp3"):
    """Generate audio using Edge-TTS with custom voice settings"""
    import edge_tts
    
    print(f"  Generating audio ({len(text)} characters)...")
    print(f"    Voice: {VOICE}")
    print(f"    Rate: {RATE}")
    print(f"    Pitch: {PITCH}")
    
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH
    )
    
    await communicate.save(output_file)
    
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        output_file
    ], capture_output=True, text=True)
    duration = float(result.stdout.strip())
    
    print(f"  ✓ Audio saved: {output_file} ({duration:.1f} seconds)")
    
    return output_file


def get_audio_duration(audio_file):
    """Get duration of audio file in seconds"""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_file
    ], capture_output=True, text=True)
    
    return float(result.stdout.strip())


def create_video(images, audio_file, output_file="output.mp4"):
    """Create video with customizable Ken Burns zoom/pan effect"""
    print("  Creating video with zoom effects...")
    print(f"    Zoom Speed: {ZOOM_SPEED}")
    print(f"    Zoom Max: {ZOOM_MAX}")
    print(f"    Style: {ZOOM_STYLE}")
    
    duration = get_audio_duration(audio_file)
    num_images = len(images)
    time_per_image = duration / num_images
    
    print(f"    Audio: {duration:.1f}s, Images: {num_images}, Per image: {time_per_image:.1f}s")
    
    temp_clips = []
    fps = 25
    
    for i, img in enumerate(images):
        clip_path = f"/tmp/clip_{i:03d}.mp4"
        frames = int(time_per_image * fps)
        
        # Determine zoom direction based on style
        if ZOOM_STYLE == 'zoom_in_only':
            zoom_in = True
        elif ZOOM_STYLE == 'zoom_out_only':
            zoom_in = False
        elif ZOOM_STYLE == 'pan':
            # Pan effect (move across image)
            zoom_in = None
        else:  # 'alternate' (default)
            zoom_in = (i % 2 == 0)
        
        if zoom_in is None:
            # Pan effect
            zoom_filter = f"zoompan=z='1.1':x='if(lte(on,1),0,x+2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        elif zoom_in:
            # Zoom in effect
            zoom_filter = f"zoompan=z='min(zoom+{ZOOM_SPEED},{ZOOM_MAX})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        else:
            # Zoom out effect
            zoom_filter = f"zoompan=z='if(lte(zoom,1.0),{ZOOM_MAX},max(1.001,zoom-{ZOOM_SPEED}))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={fps}"
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', img,
            '-vf', f"scale=4000:-1,{zoom_filter}",
            '-t', str(time_per_image),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-y',
            clip_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(clip_path):
            temp_clips.append(clip_path)
            print(f"    ✓ Clip {i+1}/{num_images}")
        else:
            print(f"    ✗ Clip {i+1} failed, using fallback")
            fallback_cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', img,
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
                '-t', str(time_per_image),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-y',
                clip_path
            ]
            subprocess.run(fallback_cmd, capture_output=True)
            if os.path.exists(clip_path):
                temp_clips.append(clip_path)
    
    if not temp_clips:
        raise Exception("No video clips created")
    
    concat_file = "/tmp/concat.txt"
    with open(concat_file, 'w') as f:
        for clip in temp_clips:
            f.write(f"file '{clip}'\n")
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-i', audio_file,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-y',
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    for clip in temp_clips:
        try:
            os.remove(clip)
        except:
            pass
    try:
        os.remove(concat_file)
    except:
        pass
    
    if result.returncode != 0:
        raise Exception(f"Video merge failed: {result.stderr}")
    
    size = os.path.getsize(output_file) // 1024 // 1024
    print(f"  ✓ Video created: {output_file} ({size}MB)")
    
    return output_file


def upload_to_drive(file_path, folder_id):
    """Upload to Google Drive using rclone"""
    print("  Uploading to Google Drive...")
    
    if not RCLONE_TOKEN:
        raise Exception("RCLONE_TOKEN not set")
    
    config = f"""[gdrive]
type = drive
scope = drive
token = {RCLONE_TOKEN}
"""
    
    config_path = "/tmp/rclone.conf"
    with open(config_path, 'w') as f:
        f.write(config)
    
    clean_title = "".join(c for c in VIDEO_TITLE if c.isalnum() or c in ' -_').strip()
    clean_title = clean_title.replace(' ', '_')[:50]
    file_name = f"{clean_title}_{JOB_ID}.mp4"
    
    cmd = [
        'rclone',
        '--config', config_path,
        'copyto',
        file_path,
        f"gdrive:Generated_Videos/{file_name}",
        '-v'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    os.remove(config_path)
    
    if result.returncode != 0:
        raise Exception(f"Upload failed: {result.stderr}")
    
    print(f"  ✓ Uploaded: {file_name}")
    
    return {
        'file_name': file_name,
        'folder_link': f"https://drive.google.com/drive/folders/{folder_id}",
        'status': 'uploaded'
    }


def save_result(status, data=None, error=None):
    """Save result JSON"""
    result = {
        'status': status,
        'job_id': JOB_ID,
        'video_title': VIDEO_TITLE
    }
    if data:
        result.update(data)
    if error:
        result['error'] = str(error)
    
    with open('result.json', 'w') as f:
        json.dump(result, f)
    
    print(f"\nResult: {json.dumps(result, indent=2)}")


async def main():
    """Main pipeline"""
    print("=" * 60)
    print("VIDEO GENERATION STARTED")
    print("=" * 60)
    print(f"Job ID:     {JOB_ID}")
    print(f"Title:      {VIDEO_TITLE}")
    print(f"Script:     {len(SCRIPT_TEXT)} characters")
    print(f"Images:     {len([u for u in IMAGE_URLS if u.strip()])} URLs")
    print(f"Voice:      {VOICE} (Rate: {RATE}, Pitch: {PITCH})")
    print(f"Zoom:       Speed={ZOOM_SPEED}, Max={ZOOM_MAX}, Style={ZOOM_STYLE}")
    print("=" * 60)
    
    try:
        print("\n[1/4] Downloading images...")
        images = download_images(IMAGE_URLS)
        if not images:
            raise Exception("No images downloaded")
        
        print("\n[2/4] Generating audio...")
        audio = await generate_audio(SCRIPT_TEXT)
        
        print("\n[3/4] Creating video...")
        video = create_video(images, audio)
        
        print("\n[4/4] Uploading...")
        if DRIVE_FOLDER_ID and RCLONE_TOKEN:
            result = upload_to_drive(video, DRIVE_FOLDER_ID)
            save_result('success', result)
        else:
            save_result('success', {'note': 'Upload skipped'})
        
        print("\n" + "=" * 60)
        print("✓ COMPLETE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        save_result('failed', error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())