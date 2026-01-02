import os
import asyncio
import json
import requests
import subprocess
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
SCRIPT_TEXT = os.environ.get('SCRIPT_TEXT', 'Welcome to this history video.')
IMAGE_URLS = os.environ.get('IMAGE_URLS', '').split(',')
VIDEO_TITLE = os.environ.get('VIDEO_TITLE', 'History Video')
JOB_ID = os.environ.get('JOB_ID', 'unknown')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')

# Voice settings (calm, slow voice for sleep content)
VOICE = "en-US-GuyNeural"  # Calm male voice
RATE = "-20%"  # Slower speech
PITCH = "-5Hz"  # Lower pitch

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
                # Determine extension
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
    
    # Create placeholder if no images downloaded
    if not downloaded:
        print("Creating placeholder image...")
        placeholder = f"{output_dir}/image_000.jpg"
        # Create simple dark image using ImageMagick/convert or Python
        subprocess.run([
            'convert', '-size', '1920x1080', 'xc:#1a1a2e',
            '-gravity', 'center', '-pointsize', '48',
            '-fill', 'white', '-annotate', '0', VIDEO_TITLE,
            placeholder
        ], capture_output=True)
        if os.path.exists(placeholder):
            downloaded.append(placeholder)
        else:
            # Fallback: create with ffmpeg
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
    """Get duration of audio file in seconds"""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_file
    ], capture_output=True, text=True)
    
    return float(result.stdout.strip())

def create_video(images, audio_file, output_file="output.mp4"):
    """Create video from images and audio using FFmpeg"""
    print("Creating video...")
    
    # Get audio duration
    duration = get_audio_duration(audio_file)
    print(f"  Audio duration: {duration:.1f} seconds")
    
    # Calculate time per image
    num_images = len(images)
    time_per_image = duration / num_images
    print(f"  Images: {num_images}, Time per image: {time_per_image:.1f}s")
    
    # Create concat file for FFmpeg
    concat_file = "concat.txt"
    with open(concat_file, 'w') as f:
        for img in images:
            f.write(f"file '{img}'\n")
            f.write(f"duration {time_per_image}\n")
        # Add last image again (FFmpeg requirement)
        f.write(f"file '{images[-1]}'\n")
    
    # FFmpeg command to create video
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
    
    # Cleanup concat file
    os.remove(concat_file)
    
    return output_file

def upload_to_drive(file_path, folder_id):
    """Upload video to Google Drive"""
    print("Uploading to Google Drive...")
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # File metadata
    file_name = f"{VIDEO_TITLE}_{JOB_ID}.mp4"
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    # Upload
    media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()
    
    # Make file accessible via link
    service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    # Get shareable link
    file = service.files().get(
        fileId=file['id'],
        fields='webViewLink, webContentLink'
    ).execute()
    
    print(f"  ✓ Uploaded: {file_name}")
    print(f"  ✓ Link: {file.get('webViewLink')}")
    
    return {
        'file_id': file.get('id'),
        'view_link': file.get('webViewLink'),
        'download_link': file.get('webContentLink')
    }

def save_result(status, data=None, error=None):
    """Save result to JSON for webhook notification"""
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
    """Main video generation pipeline"""
    print("=" * 50)
    print("VIDEO GENERATION STARTED")
    print("=" * 50)
    print(f"Job ID: {JOB_ID}")
    print(f"Title: {VIDEO_TITLE}")
    print(f"Script length: {len(SCRIPT_TEXT)} characters")
    print(f"Image URLs: {len(IMAGE_URLS)}")
    print("=" * 50)
    
    try:
        # Step 1: Download images
        images = download_images(IMAGE_URLS)
        if not images:
            raise Exception("No images downloaded")
        
        # Step 2: Generate audio
        audio_file = await generate_audio(SCRIPT_TEXT)
        
        # Step 3: Create video
        video_file = create_video(images, audio_file)
        
        # Step 4: Upload to Drive
        if DRIVE_FOLDER_ID:
            drive_result = upload_to_drive(video_file, DRIVE_FOLDER_ID)
            save_result('success', drive_result)
        else:
            save_result('success', {'note': 'No Drive folder configured'})
        
        print("\n" + "=" * 50)
        print("VIDEO GENERATION COMPLETE!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        save_result('failed', error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main())