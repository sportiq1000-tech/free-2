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

from text_cleaner import (
    clean_gutenberg_text,
    clean_for_narration
)


# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')


def select_random_document(
    category: str = None,
    target_minutes: int = 10,
    groq_api_key: str = None
) -> Optional[Dict]:
    """
    Simplified Pipeline: Fetch → Regex Clean → Return
    Reserves LLM credits for script generation.
    """
    
    api_key = groq_api_key or GROQ_API_KEY
    
    print("\n" + "=" * 70)
    print("📚 BUREAUCRATIC ARCHIVIST - DOCUMENT PIPELINE (OPTIMIZED)")
    print("=" * 70)
    print(f"Source: Project Gutenberg (100% Public Domain)")
    print(f"Target: {target_minutes} minutes")
    print(f"Category: {category or 'random'}")
    print("=" * 70)
    
    # 1. FETCH
    print("\n📥 STEP 1: Fetching Document...")
    document = fetch_gutenberg_document(category=category)
    
    if not document:
        print("  ❌ Failed to fetch document")
        return None
    
    metadata = document['metadata']
    raw_text = document['text']
    
    # 2. CLEAN (Regex only)
    print("\n🧹 STEP 2: Cleaning Text (Regex)...")
    cleaned_result = clean_for_narration(
        raw_text,
        target_minutes=target_minutes,
        api_key=api_key
    )
    
    cleaned_text = cleaned_result['text']
    word_count = cleaned_result['word_count']
    
    # 3. PREPARE OUTPUT
    print("\n📦 STEP 3: Preparing Output...")
    
    # Determine document type
    if category:
        document_type = category
    elif 'rule' in metadata['title'].lower():
        document_type = 'parliamentary'
    elif 'manual' in metadata['title'].lower():
        document_type = 'manuals'
    else:
        document_type = 'government'

    # Placeholders
    images = [f"paper_texture_{i}.jpg" for i in range(5)]
    
    quality_details = {
        "source": "Project Gutenberg",
        "word_count": word_count,
        "cleaning_method": "Regex"
    }

    print("\n" + "=" * 70)
    print("✅ DOCUMENT READY (Zero LLM Used)")
    print("=" * 70)
    print(f"Title: {metadata['title']}")
    print(f"Words: {word_count:,}")
    print("=" * 70)
    
    return {
        "metadata": metadata,
        "text": cleaned_text,
        "images": images,
        "document_type": document_type,
        "quality_score": 1.0,
        "quality_details": quality_details
    }


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