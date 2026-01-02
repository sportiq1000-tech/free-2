import os
import asyncio
import json
import requests
import subprocess
from pathlib import Path
import urllib.parse
import random

# Configuration from environment variables
SCRIPT_TEXT = os.environ.get('SCRIPT_TEXT', 'Welcome to this history video.')
IMAGE_URLS = os.environ.get('IMAGE_URLS', '').split(',')
VIDEO_TITLE = os.environ.get('VIDEO_TITLE', 'History Video')
JOB_ID = os.environ.get('JOB_ID', 'unknown')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')
RCLONE_TOKEN = os.environ.get('RCLONE_TOKEN', '')
IMAGE_SOURCE = os.environ.get('IMAGE_SOURCE', 'lexica')  # lexica, unsplash, pexels, direct

# Voice settings (calm, slow voice for sleep content)
VOICE = "en-US-GuyNeural"
RATE = "-15%"
PITCH = "-3Hz"

# API Keys (optional - for Unsplash/Pexels)
UNSPLASH_API_KEY = os.environ.get('UNSPLASH_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')


def fetch_lexica_images(query, count=5):
    """Fetch images from Lexica.art (no watermark, no API key needed)"""
    print(f"  Fetching from Lexica: {query}")
    
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://lexica.art/api/v1/search?q={encoded_query}"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            
            # Get image URLs (use srcSmall for faster download, src for full quality)
            urls = []
            for img in images[:count * 2]:  # Get extra in case some fail
                if 'src' in img:
                    urls.append(img['src'])
                if len(urls) >= count:
                    break
            
            print(f"  Found {len(urls)} images from Lexica")
            return urls
        else:
            print(f"  Lexica API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  Lexica error: {e}")
        return []


def fetch_unsplash_images(query, count=5):
    """Fetch images from Unsplash (requires free API key)"""
    if not UNSPLASH_API_KEY:
        print("  Unsplash API key not set, skipping...")
        return []
    
    print(f"  Fetching from Unsplash: {query}")
    
    try:
        url = f"https://api.unsplash.com/search/photos?query={urllib.parse.quote(query)}&per_page={count}"
        headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            urls = [img['urls']['regular'] for img in data.get('results', [])]
            print(f"  Found {len(urls)} images from Unsplash")
            return urls
        else:
            print(f"  Unsplash API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  Unsplash error: {e}")
        return []


def fetch_pexels_images(query, count=5):
    """Fetch images from Pexels (requires free API key)"""
    if not PEXELS_API_KEY:
        print("  Pexels API key not set, skipping...")
        return []
    
    print(f"  Fetching from Pexels: {query}")
    
    try:
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={count}"
        headers = {"Authorization": PEXELS_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            urls = [img['src']['large'] for img in data.get('photos', [])]
            print(f"  Found {len(urls)} images from Pexels")
            return urls
        else:
            print(f"  Pexels API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  Pexels error: {e}")
        return []


def download_images(urls_or_queries, output_dir="images", count_per_query=3):
    """Download images from URLs or search queries"""
    Path(output_dir).mkdir(exist_ok=True)
    downloaded = []
    
    all_urls = []
    
    for item in urls_or_queries:
        item = item.strip()
        if not item:
            continue
        
        # Check if it's a direct URL or a search query
        if item.startswith('http://') or item.startswith('https://'):
            # Skip pollinations URLs (have watermarks)
            if 'pollinations.ai' in item:
                print(f"  Skipping Pollinations URL (has watermark): {item[:50]}...")
                # Extract the prompt and search Lexica instead
                if '/prompt/' in item:
                    query = item.split('/prompt/')[-1].split('?')[0]
                    query = urllib.parse.unquote(query).replace('%20', ' ')
                    print(f"  Searching Lexica for: {query}")
                    lexica_urls = fetch_lexica_images(query, count_per_query)
                    all_urls.extend(lexica_urls)
            else:
                all_urls.append(item)
        else:
            # It's a search query - fetch from Lexica
            print(f"  Search query detected: {item}")
            lexica_urls = fetch_lexica_images(item, count_per_query)
            all_urls.extend(lexica_urls)
    
    # If no URLs found, try generic historical images
    if not all_urls:
        print("  No images found, trying fallback search...")
        all_urls = fetch_lexica_images("ancient history painting", 5)
    
    # Download the images
    for i, url in enumerate(all_urls):
        if len(downloaded) >= 10:  # Max 10 images
            break
            
        try:
            print(f"  Downloading image {i+1}: {url[:60]}...")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                ext = 'png' if 'png' in content_type else 'jpg'
                
                filepath = f"{output_dir}/image_{len(downloaded):03d}.{ext}"
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Verify file size (skip tiny/broken images)
                if os.path.getsize(filepath) > 10000:  # > 10KB
                    downloaded.append(filepath)
                    print(f"    ✓ Saved: {filepath}")
                else:
                    os.remove(filepath)
                    print(f"    ✗ Skipped: too small")
            else:
                print(f"    ✗ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # Create placeholder if no images downloaded
    if not downloaded:
        print("  Creating placeholder image...")
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
    
    print(f"  Generating audio ({len(text)} characters)...")
    
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


def create_video_with_effects(images, audio_file, output_file="output.mp4"):
    """Create video with Ken Burns effect (zoom and pan)"""
    print("Creating video with zoom/pan effects...")
    
    duration = get_audio_duration(audio_file)
    print(f"  Audio duration: {duration:.1f} seconds")
    
    num_images = len(images)
    time_per_image = duration / num_images
    print(f"  Images: {num_images}, Time per image: {time_per_image:.1f}s")
    
    # Create individual video clips with zoom effect for each image
    temp_videos = []
    
    for i, img in enumerate(images):
        temp_video = f"/tmp/clip_{i:03d}.mp4"
        
        # Alternate between zoom in and zoom out
        if i % 2 == 0:
            # Zoom in effect
            zoom_filter = f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(time_per_image*25)}:s=1920x1080:fps=25"
        else:
            # Zoom out effect
            zoom_filter = f"scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(time_per_image*25)}:s=1920x1080:fps=25"
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', img,
            '-vf', zoom_filter,
            '-t', str(time_per_image),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-y',
            temp_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_video):
            temp_videos.append(temp_video)
            print(f"    ✓ Created clip {i+1}/{num_images}")
        else:
            print(f"    ✗ Failed clip {i+1}: {result.stderr[:100] if result.stderr else 'unknown error'}")
    
    if not temp_videos:
        print("  Falling back to simple slideshow...")
        return create_video_simple(images, audio_file, output_file)
    
    # Concatenate all clips
    concat_file = "/tmp/concat_clips.txt"
    with open(concat_file, 'w') as f:
        for v in temp_videos:
            f.write(f"file '{v}'\n")
    
    # Merge clips with audio
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
    
    # Cleanup temp files
    for v in temp_videos:
        try:
            os.remove(v)
        except:
            pass
    try:
        os.remove(concat_file)
    except:
        pass
    
    if result.returncode != 0:
        print(f"  ✗ FFmpeg error: {result.stderr}")
        print("  Falling back to simple slideshow...")
        return create_video_simple(images, audio_file, output_file)
    
    print(f"  ✓ Video created with effects: {output_file}")
    return output_file


def create_video_simple(images, audio_file, output_file="output.mp4"):
    """Create simple slideshow video (fallback)"""
    print("Creating simple slideshow video...")
    
    duration = get_audio_duration(audio_file)
    num_images = len(images)
    time_per_image = duration / num_images
    
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
    
    os.remove(concat_file)
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr}")
    
    print(f"  ✓ Video created: {output_file}")
    return output_file


def upload_to_drive_rclone(file_path, folder_id):
    """Upload video to Google Drive using rclone"""
    print("Uploading to Google Drive (rclone)...")
    
    if not RCLONE_TOKEN:
        raise Exception("RCLONE_TOKEN environment variable not set")
    
    rclone_config = f"""[gdrive]
type = drive
scope = drive
token = {RCLONE_TOKEN}
"""
    
    config_path = "/tmp/rclone.conf"
    with open(config_path, 'w') as f:
        f.write(rclone_config)
    
    clean_title = "".join(c for c in VIDEO_TITLE if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_title = clean_title.replace(' ', '_')
    if not clean_title:
        clean_title = "video"
    file_name = f"{clean_title}_{JOB_ID}.mp4"
    
    print(f"  File name: {file_name}")
    
    cmd = [
        'rclone',
        '--config', config_path,
        'copyto',
        file_path,
        f"gdrive:Generated_Videos/{file_name}",
        '-v',
        '--retries', '3'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  rclone error: {result.stderr}")
        raise Exception(f"rclone upload failed: {result.stderr}")
    
    try:
        os.remove(config_path)
    except:
        pass
    
    print(f"  ✓ Upload complete: {file_name}")
    
    return {
        'file_name': file_name,
        'folder_link': f"https://drive.google.com/drive/folders/{folder_id}",
        'status': 'uploaded'
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
    print("=" * 60)
    print("VIDEO GENERATION STARTED")
    print("=" * 60)
    print(f"Job ID:        {JOB_ID}")
    print(f"Title:         {VIDEO_TITLE}")
    print(f"Script length: {len(SCRIPT_TEXT)} characters")
    print(f"Image inputs:  {len([u for u in IMAGE_URLS if u.strip()])}")
    print(f"Drive Folder:  {DRIVE_FOLDER_ID[:20] + '...' if DRIVE_FOLDER_ID else 'Not set'}")
    print(f"Rclone Token:  {'Set ✓' if RCLONE_TOKEN else 'Not set ✗'}")
    print("=" * 60)
    
    try:
        # Step 1: Download images
        print("\n[STEP 1/4] Fetching images...")
        images = download_images(IMAGE_URLS)
        if not images:
            raise Exception("No images available")
        print(f"  Total images: {len(images)}")
        
        # Step 2: Generate audio
        print("\n[STEP 2/4] Generating audio...")
        audio_file = await generate_audio(SCRIPT_TEXT)
        
        # Step 3: Create video with effects
        print("\n[STEP 3/4] Creating video...")
        video_file = create_video_with_effects(images, audio_file)
        
        # Step 4: Upload to Drive
        print("\n[STEP 4/4] Uploading to Google Drive...")
        if DRIVE_FOLDER_ID and RCLONE_TOKEN:
            drive_result = upload_to_drive_rclone(video_file, DRIVE_FOLDER_ID)
            save_result('success', drive_result)
        else:
            missing = []
            if not DRIVE_FOLDER_ID:
                missing.append("DRIVE_FOLDER_ID")
            if not RCLONE_TOKEN:
                missing.append("RCLONE_TOKEN")
            print(f"  ⚠ Skipping upload - missing: {', '.join(missing)}")
            save_result('success', {'note': f'Upload skipped - missing: {", ".join(missing)}'})
        
        print("\n" + "=" * 60)
        print("✓ VIDEO GENERATION COMPLETE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        save_result('failed', error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())