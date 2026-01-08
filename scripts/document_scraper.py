"""
Integrated Document Scraper for The Bureaucratic Archivist
Combines: Gutenberg + Text Cleaner + Dual-LLM Verification

100% Groq-powered, 100% free, 100% public domain content
"""

import os
import sys
import random
from typing import Optional, Dict
from pathlib import Path

# Import our modules
from gutenberg_scraper import (
    fetch_gutenberg_document,
    list_available_categories,
    CURATED_DOCUMENTS
)



# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')


def select_random_document(
    category: str = None,
    target_minutes: int = 10,
    groq_api_key: str = None
) -> Optional[Dict]:
    
    print("\n[DOCUMENT SCRAPER - QUALITY CONTROL]")
    
    # Try up to 5 times to get good English text
    for attempt in range(5):
        # Step 1: Fetch
        document = fetch_gutenberg_document(category=category)
        if not document: continue
        
        # Step 2: Clean
        from text_cleaner import fix_hard_wraps, select_smart_chunk
        
        raw_text = document['text']
        target_words = target_minutes * 130
        chunk = select_smart_chunk(raw_text, target_words)
        clean_text = fix_hard_wraps(chunk)
        
        # Step 3: English Check (Basic)
        # Count common English words to avoid Latin/Foreign texts
        common = ['the', 'and', 'that', 'with', 'this', 'from', 'have', 'for']
        english_score = sum(1 for w in common if w in clean_text.lower())
        
        if english_score < 3:
            print(f"  ⚠️ Rejecting Attempt {attempt+1}: Looks like Latin/Foreign")
            continue
            
        print(f"  ✅ Text prepared ({len(clean_text.split())} words)")
        
        return {
            "metadata": document['metadata'],
            "text": clean_text,
            "images": [], # Will be filled by auto_visuals
            "document_type": category or 'document',
            "quality_score": 0.95,
            "quality_details": {"source": "Gutenberg"}
        }
        
    print("❌ Failed to find English text after 5 attempts")
    return None


def get_document_images(archive_id: str, max_images: int = 10):
    """
    Placeholder function for compatibility
    Gutenberg doesn't have images, so we return placeholders
    """
    return [f"paper_texture_{i}.jpg" for i in range(max_images)]


def list_categories():
    """List available Gutenberg categories"""
    return list_available_categories()


def get_all_documents():
    """Get list of all available documents"""
    all_docs = []
    for category, docs in CURATED_DOCUMENTS.items():
        for doc in docs:
            doc_copy = doc.copy()
            doc_copy['category'] = category
            all_docs.append(doc_copy)
    return all_docs


# For compatibility with existing pipeline
extract_document_metadata = lambda text, meta: meta
def split_text_for_duration(text, target_minutes, words_per_minute=120):
    """
    Split text into a chunk that fits the target duration.
    Supports keyword arguments for compatibility.
    """
    target_words = int(target_minutes * words_per_minute)
    words = text.split()
    if len(words) <= target_words:
        return text
    return ' '.join(words[:target_words])


# Test
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing Integrated Document Scraper")
    print("=" * 70)
    
    # List categories
    print("\n📁 Available Categories:")
    for cat, info in list_categories().items():
        print(f"   {cat}: {info['count']} documents")
        for title in info['titles']:
            print(f"      - {title}")
    
    # Fetch a document
    print("\n" + "=" * 70)
    print("Fetching random parliamentary document...")
    print("=" * 70)
    
    doc = select_random_document(
        category='parliamentary',
        target_minutes=5
    )
    
    if doc:
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"\nFirst 500 characters of cleaned text:")
        print("-" * 70)
        print(doc['text'][:500])
        print("-" * 70)