"""
Main Pipeline for The Bureaucratic Archivist
Orchestrates the complete video creation process
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime

# Import our modules
from document_scraper import select_random_document
from scriptenhancer import create_full_script
from voice_generator import VoiceGenerator
from visual_generator import VisualGenerator
from video_assembler import VideoAssembler


class BureaucraticArchivistPipeline:
    def __init__(self, output_dir="output", groq_api_key=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.groq_api_key = groq_api_key or os.environ.get('GROQ_API_KEY', '')
        
        # Initialize components
        self.voice_gen = VoiceGenerator()
        self.visual_gen = VisualGenerator(assets_dir=str(self.output_dir / "assets"))
        self.video_assembler = VideoAssembler(output_dir=str(self.output_dir))
        
        # History tracking
        self.history_file = self.output_dir / "video_history.json"
        self.history = self._load_history()
    
    def _load_history(self):
        """Load creation history"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {
            'videos': [],
            'documents_used': [],
            'voices_used': []
        }
    
    def _save_history(self):
        """Save creation history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def create_video(
        self, 
        document_type=None, 
        target_minutes=10,
        use_groq_intro=True
    ):
        """
        Create a complete video from start to finish
        
        Args:
            document_type: Type of document ('maritime_log', 'patent', etc.) or None for random
            target_minutes: Target video duration
            use_groq_intro: Use Groq for curator intro (requires API key)
        
        Returns:
            dict with paths and metadata
        """
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_id = f"archive_{timestamp}"
        
        print("\n" + "="*70)
        print(f"🎬 THE BUREAUCRATIC ARCHIVIST - Video Creation Pipeline")
        print("="*70)
        print(f"Video ID: {video_id}")
        print(f"Target Duration: {target_minutes} minutes")
        print("="*70 + "\n")
        
        try:
            # ============================================
            # STEP 1: FETCH DOCUMENT
            # ============================================
            print("📜 STEP 1: Fetching Historical Document")
            print("-" * 70)
            
            document = select_random_document(
                document_type=document_type,
                min_words=800,
                max_words=50000
            )
            
            if not document:
                raise Exception("Could not fetch suitable document")
            
            metadata = document['metadata']
            doc_text = document['text']
            doc_images = document['images']
            doc_type = document['document_type']
            
            print(f"✓ Document: {metadata['title'][:60]}...")
            print(f"✓ Year: {metadata['year']}")
            print(f"✓ Words: {metadata['word_count']}")
            print(f"✓ Images: {len(doc_images)}")
            
            # ============================================
            # STEP 2: CREATE SCRIPT
            # ============================================
            print("\n✏️ STEP 2: Creating Enhanced Script")
            print("-" * 70)
            
            if use_groq_intro and self.groq_api_key:
                script_data = create_full_script(
                    doc_text,
                    metadata,
                    doc_type,
                    target_minutes,
                    groq_api_key=self.groq_api_key
                )
                print(f"✓ Used Groq for curator intro")
            else:
                # Fallback: basic script without Groq
                print(f"⚠️ Groq API key not found, using fallback intro")
                from scriptenhancer import generate_fallback_intro, generate_outro
                from document_scraper import split_text_for_duration
                
                intro = generate_fallback_intro(metadata, doc_type)
                outro = generate_outro(metadata, target_minutes)
                main_text = split_text_for_duration(doc_text, target_minutes - 2)
                
                full_script = f"{intro}\n\n{main_text}\n\n{outro}"
                
                script_data = {
                    'full_script': full_script,
                    'intro': intro,
                    'main_text': main_text,
                    'outro': outro,
                    'comparisons': [],
                    'word_count': len(full_script.split()),
                    'estimated_minutes': len(full_script.split()) / 120
                }
            
            print(f"✓ Script: {script_data['word_count']} words")
            print(f"✓ Est. duration: {script_data['estimated_minutes']:.1f} minutes")
            
            # ============================================
            # STEP 3: GENERATE AUDIO
            # ============================================
            print("\n🎙️ STEP 3: Generating Narration")
            print("-" * 70)
            
            audio_path = self.output_dir / f"{video_id}_audio.mp3"
            
            voice_settings = self.voice_gen.generate_from_script(
                script_data,
                str(audio_path)
            )
            
            print(f"✓ Audio saved: {audio_path.name}")
            
            # ============================================
            # STEP 4: PROCESS VISUALS
            # ============================================
            print("\n🖼️ STEP 4: Processing Visuals")
            print("-" * 70)
            
            image_dir = self.output_dir / f"{video_id}_images"
            
            if doc_images and len(doc_images) > 0:
                processed_images = self.visual_gen.process_document_images(
                    doc_images,
                    str(image_dir),
                    max_images=min(10, len(doc_images))
                )
            else:
                # Fallback: create paper background
                print("⚠️ No document images, creating paper background...")
                image_dir.mkdir(exist_ok=True)
                paper_path = image_dir / "paper.jpg"
                self.visual_gen.create_paper_background(str(paper_path))
                
                processed_path = image_dir / "processed_00.jpg"
                self.visual_gen.apply_archival_effect(str(paper_path), str(processed_path))
                processed_images = [str(processed_path)]
            
            print(f"✓ Processed {len(processed_images)} images")
            
            # ============================================
            # STEP 5: GENERATE THUMBNAIL
            # ============================================
            print("\n📸 STEP 5: Creating Thumbnail")
            print("-" * 70)
            
            thumbnail_path = self.output_dir / f"{video_id}_thumbnail.jpg"
            
            self.visual_gen.generate_thumbnail(
                metadata['title'][:60],
                str(metadata['year']) if metadata['year'] else 'Unknown',
                str(thumbnail_path),
                style='dark'
            )
            
            # ============================================
            # STEP 6: ASSEMBLE VIDEO
            # ============================================
            print("\n🎬 STEP 6: Assembling Video")
            print("-" * 70)
            
            video_path = self.output_dir / f"{video_id}.mp4"
            
            zoom_settings = self.video_assembler.get_randomized_zoom_settings()
            
            self.video_assembler.create_video(
                processed_images,
                str(audio_path),
                str(video_path),
                zoom_settings
            )
            
            # ============================================
            # STEP 7: GENERATE METADATA
            # ============================================
            print("\n📝 STEP 7: Generating Metadata")
            print("-" * 70)
            
            video_metadata = self._generate_metadata(
                metadata,
                doc_type,
                script_data,
                voice_settings,
                zoom_settings
            )
            
            metadata_path = self.output_dir / f"{video_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(video_metadata, f, indent=2)
            
            print(f"✓ Metadata saved")
            
            # ============================================
            # STEP 8: UPDATE HISTORY
            # ============================================
            self.history['videos'].append({
                'id': video_id,
                'created': timestamp,
                'document_id': metadata['archive_id'],
                'title': video_metadata['title'],
                'duration_minutes': script_data['estimated_minutes']
            })
            self.history['documents_used'].append(metadata['archive_id'])
            self.history['voices_used'].append(voice_settings['voice'])
            
            self._save_history()
            
            # ============================================
            # COMPLETE!
            # ============================================
            print("\n" + "="*70)
            print("✅ VIDEO CREATION COMPLETE!")
            print("="*70)
            print(f"\n📁 Files Created:")
            print(f"   Video:     {video_path.name}")
            print(f"   Audio:     {audio_path.name}")
            print(f"   Thumbnail: {thumbnail_path.name}")
            print(f"   Metadata:  {metadata_path.name}")
            
            print(f"\n📋 Suggested Title:")
            print(f"   {video_metadata['title']}")
            
            print(f"\n📋 Description Preview:")
            print(f"   {video_metadata['description'][:150]}...")
            
            print("\n" + "="*70 + "\n")
            
            return {
                'video_path': str(video_path),
                'audio_path': str(audio_path),
                'thumbnail_path': str(thumbnail_path),
                'metadata_path': str(metadata_path),
                'metadata': video_metadata
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _generate_metadata(self, doc_metadata, doc_type, script_data, voice_settings, zoom_settings):
        """Generate YouTube metadata"""
        
        # Title variations
        title_templates = [
            f"{doc_metadata['title'][:60]} | Historical Archive Reading",
            f"[{doc_metadata['year']}] {doc_metadata['title'][:50]} | Archival Document",
            f"Archive Reading: {doc_metadata['title'][:50]} ({doc_metadata['year']})",
            f"{doc_type.replace('_', ' ').title()} from {doc_metadata['year']} | Sleep & History",
        ]
        
        title = random.choice(title_templates)
        
        # Description
        description = f"""📜 {doc_metadata['title']}

This reading presents an authentic historical document from {doc_metadata['year']}, preserved in public archives.

📋 Document Details:
• Title: {doc_metadata['title']}
• Year: {doc_metadata['year']}
• Type: {doc_type.replace('_', ' ').title()}
• Source: Internet Archive
• Duration: {script_data['estimated_minutes']:.0f} minutes

🎧 Perfect for:
• Sleep and relaxation
• Historical education
• Background study
• ASMR & calm listening

📚 About The Bureaucratic Archivist:
We read authentic historical documents preserved in public archives. Every recording features real primary sources, presented with thoughtful context.

#history #archives #sleep #asmr #documentary #{doc_type}

—
📝 All documents are in the public domain.
🔗 Original: https://archive.org/details/{doc_metadata['archive_id']}
"""
        
        # Tags
        tags = [
            "history",
            "archives",
            "historical documents",
            "sleep",
            "relaxation",
            "asmr",
            "documentary",
            doc_type.replace('_', ' '),
            str(doc_metadata['year']),
            "public domain",
            "educational"
        ]
        
        return {
            'title': title,
            'description': description,
            'tags': tags,
            'category': '27',  # Education
            'privacy': 'public',
            'document': {
                'archive_id': doc_metadata['archive_id'],
                'title': doc_metadata['title'],
                'year': doc_metadata['year'],
                'type': doc_type
            },
            'production': {
                'voice': voice_settings['voice'],
                'voice_rate': voice_settings['rate'],
                'voice_pitch': voice_settings['pitch'],
                'zoom_style': zoom_settings['style']
            }
        }


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create Bureaucratic Archivist video')
    parser.add_argument('--type', help='Document type (maritime_log, patent, etc.)')
    parser.add_argument('--duration', type=int, default=10, help='Target duration in minutes')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--no-groq', action='store_true', help='Skip Groq intro generation')
    
    args = parser.parse_args()
    
    pipeline = BureaucraticArchivistPipeline(output_dir=args.output)
    
    result = pipeline.create_video(
        document_type=args.type,
        target_minutes=args.duration,
        use_groq_intro=not args.no_groq
    )
    
    print("🎉 Video ready for upload!")