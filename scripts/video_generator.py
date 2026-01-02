import os
import asyncio
import json
import requests
import subprocess
from pathlib import Path

# Configuration
SCRIPT_TEXT = os.environ.get('SCRIPT_TEXT', 'Welcome to this history video.')
IMAGE_URLS = os.environ.get('IMAGE_URLS', '').split(',')
VIDEO_TITLE = os.environ.get('VIDEO_TITLE', 'History Video')
JOB_ID = os.environ.get('JOB_ID', 'unknown')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')
RCLONE_TOKEN = os.environ.get('RCLONE_TOKEN', '')

# Voice settings
VOICE = "en-US-GuyNeural"
RATE = "-20%"
PITCH = "-5Hz"

def download_images(urls, output_dir="images"):
    """Download images from URLs"""
    Path(output_dir).mkdir(exist_ok=True)
    downloaded = []
    
    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue
            
        try:
            print(f"Downloading image {i+1}: {url[:80]}...")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                ext = 'jpg' if 'jpeg' in content_type or 'jpg' in content_type else 'png'
                
                filepath = f"{output_dir}/image_{i:03d}.{ext}"
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                downloaded.append(filepath)
                print(f"  ✓ Saved: {filepath}")
            else:
                print(f"  ✗ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Create placeholder if no images
    if not downloaded:
        print("Creating placeholder image...")
        placeholder = f"{output_dir}/image_000.jpg"
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', 'color=c=0x1a1a2e:s=1920x1080:d=1',
            '-frames:v', '1', placeholder, '-y'
        ], capture_output=True)
        if os.path.exists(placeholder):
            downloaded.append(placeholder)
    
    return downloaded

async def generate_audio(text, output_file="audio.mp3"):
    """Generate audio using Edge-TTS"""
    import edge_tts
    
    print(f"Generating audio ({len(text)} characters)...")
    
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH
    )
    
    await communicate.save(output_file)
    print(f"  ✓ Audio saved: {output_file}")
    
    return output_file

def get_audio_duration(audio_file):
    """Get duration of audio file"""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_file
    ], capture_output=True, text=True)
    
    return float(result.stdout.strip())

def create_video(images, audio_file, output_file="output.mp4"):
    """Create video from images and audio"""
    print("Creating video...")
    
    duration = get_audio_duration(audio_file)
    print(f"  Audio duration: {duration:.1f} seconds")
    
    num_images = len(images)
    time_per_image = duration / num_images
    print(f"  Images: {num_images}, Time per image: {time_per_image:.1f}s")
    
    concat_file = "concat.txt"
    with open(concat_file, 'w') as f:
        for img in images:
            f.write(f"file '{img}'\n")
            f.write(f"duration {time_per_image}\n")
        f.write(f"file '{images[-1]}'\n")
    
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
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        '-shortest',
        '-y',
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ✗ FFmpeg error: {result.stderr}")
        raise Exception(f"FFmpeg failed: {result.stderr}")
    
    print(f"  ✓ Video created: {output_file}")
    os.remove(concat_file)
    
    return output_file

def upload_to_drive(file_path, folder_id):
    """Upload video to Google Drive using rclone"""
    print("Uploading to Google Drive...")
    
    if not RCLONE_TOKEN:
        raise Exception("RCLONE_TOKEN not set")
    
    # Create rclone config
    rclone_config = f"""[gdrive]
type = drive
scope = drive
token = {RCLONE_TOKEN}
"""
    
    config_path = "/tmp/rclone.conf"
    with open(config_path, 'w') as f:
        f.write(rclone_config)
    
    # File name
    file_name = f"{VIDEO_TITLE}_{JOB_ID}.mp4"
    
    # Copy file to Drive
    cmd = [
        'rclone',
        '--config', config_path,
        'copyto',
        file_path,
        f"gdrive:Generated_Videos/{file_name}",
        '-v'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"rclone output: {result.stdout}")
    
    if result.returncode != 0:
        print(f"rclone error: {result.stderr}")
        raise Exception(f"rclone failed: {result.stderr}")
    
    # Cleanup
    os.remove(config_path)
    
    print(f"  ✓ Uploaded: {file_name}")
    
    return {
        'file_name': file_name,
        'folder_link': f"https://drive.google.com/drive/folders/{folder_id}",
        'status': 'uploaded'
    }

def save_result(status, data=None, error=None):
    """Save result to JSON"""
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
    print("=" * 50)
    print("VIDEO GENERATION STARTED")
    print("=" * 50)
    print(f"Job ID: {JOB_ID}")
    print(f"Title: {VIDEO_TITLE}")
    print(f"Script length: {len(SCRIPT_TEXT)} characters")
    print(f"Image URLs: {len(IMAGE_URLS)}")
    print("=" * 50)
    
    try:
        images = download_images(IMAGE_URLS)
        if not images:
            raise Exception("No images downloaded")
        
        audio_file = await generate_audio(SCRIPT_TEXT)
        video_file = create_video(images, audio_file)
        
        if DRIVE_FOLDER_ID and RCLONE_TOKEN:
            drive_result = upload_to_drive(video_file, DRIVE_FOLDER_ID)
            save_result('success', drive_result)
        else:
            save_result('success', {'note': 'No Drive upload configured'})
        
        print("\n" + "=" * 50)
        print("VIDEO GENERATION COMPLETE!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        save_result('failed', error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main())