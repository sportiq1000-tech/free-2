"""
Document Scraper for The Bureaucratic Archivist
Fetches public domain documents from Internet Archive and other sources
"""

import os
import requests
import json
import random
import re
from datetime import datetime
from typing import Optional, Dict, List

# Configuration
INTERNET_ARCHIVE_API = "https://archive.org/advancedsearch.php"

# Document type configurations
DOCUMENT_TYPES = {
    "maritime_log": {
        "search_terms": ["ship log", "maritime log", "captain's log", "voyage journal", "naval log"],
        "date_range": "1700-1920",
        "collections": ["americana", "naval", "maritime"]
    },
    "patent": {
        "search_terms": ["patent", "invention", "patent drawing", "patent specification"],
        "date_range": "1790-1930",
        "collections": ["patents", "americana"]
    },
    "city_ordinance": {
        "search_terms": ["city ordinance", "municipal law", "town regulation", "bylaw"],
        "date_range": "1800-1930",
        "collections": ["americana", "governmentpublications"]
    },
    "census_record": {
        "search_terms": ["census", "population schedule", "enumeration"],
        "date_range": "1790-1940",
        "collections": ["census", "americana"]
    },
    "court_record": {
        "search_terms": ["court record", "legal proceeding", "trial transcript"],
        "date_range": "1800-1930",
        "collections": ["americana", "law"]
    },
    "government_report": {
        "search_terms": ["government report", "congressional report", "official report"],
        "date_range": "1800-1930",
        "collections": ["governmentpublications", "americana"]
    }
}


def search_internet_archive(
    query: str,
    document_type: str = "maritime_log",
    max_results: int = 10
) -> List[Dict]:
    """Search Internet Archive for documents"""
    
    config = DOCUMENT_TYPES.get(document_type, DOCUMENT_TYPES["maritime_log"])
    
    # Build search query
    search_term = random.choice(config["search_terms"])
    if query:
        search_term = f"{search_term} {query}"
    
    # Add date filter for public domain
    year_range = config["date_range"]
    
    params = {
        "q": f"{search_term} AND mediatype:texts AND year:[{year_range.replace('-', ' TO ')}]",
        "fl[]": ["identifier", "title", "creator", "date", "description", "subject"],
        "sort[]": "downloads desc",
        "rows": max_results,
        "page": 1,
        "output": "json"
    }
    
    try:
        print(f"  Searching Internet Archive: {search_term}")
        response = requests.get(INTERNET_ARCHIVE_API, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            print(f"  Found {len(docs)} documents")
            return docs
        else:
            print(f"  Archive API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  Archive search error: {e}")
        return []


def get_document_text(archive_id: str) -> Optional[str]:
    """Fetch full text of a document from Internet Archive"""
    
    # Try multiple text formats
    formats = [f"{archive_id}_djvu.txt", f"{archive_id}_text.txt", f"{archive_id}.txt"]
    
    for fmt in formats:
        text_url = f"https://archive.org/download/{archive_id}/{fmt}"
        try:
            print(f"  Fetching text: {fmt}")
            response = requests.get(text_url, timeout=30)
            
            if response.status_code == 200:
                text = response.text
                # Filter out accidental HTML responses
                if "<html" in text[:100].lower():
                    continue
                print(f"  Retrieved {len(text)} characters")
                return text
        except Exception as e:
            continue
            
    print(f"  Text not available for {archive_id}")
    return None


def get_document_images(archive_id: str, max_images: int = 10) -> List[str]:
    """Get image URLs for document pages"""
    
    image_urls = []
    
    # 1. Always add the thumbnail/cover
    image_urls.append(f"https://archive.org/services/img/{archive_id}")
    
    # 2. Try standard page patterns
    # We generate potential URLs but rely on visual_generator to handle 404s
    # This prevents the scraper from being too slow checking every image
    base_url = f"https://archive.org/download/{archive_id}"
    
    for i in range(1, max_images + 1):
        # Pattern 1: Simple n1.jpg
        image_urls.append(f"{base_url}/page/n{i}.jpg")
        
        # Pattern 2: Padded numbers
        pad = str(i).zfill(4)
        image_urls.append(f"{base_url}/{archive_id}_jp2/page_{pad}.jpg")
        
    return image_urls


def clean_document_text(raw_text: str) -> str:
    """Clean OCR text from historical documents - BUG FIXED VERSION"""
    
    if not raw_text:
        return ""
    
    text = raw_text
    
    # Define fixes: (Pattern, Replacement, Flags [Optional])
    ocr_fixes = [
        (r'\n{3,}', '\n\n', 0),           # Multiple newlines to double
        (r'[ \t]+', ' ', 0),               # Multiple spaces to single
        (r'-\n', '', 0),                   # Hyphenated line breaks
        (r'\n([a-z])', r' \1', 0),         # Join broken sentences
        (r'[|]', 'I', 0),                  # Common OCR error: | for I
        (r'(?<=[a-z])0(?=[a-z])', 'o', 0), # 0 for o in words
        (r'(?<=[a-z])1(?=[a-z])', 'l', 0), # 1 for l in words
        (r'["""]', '"', 0),                # Normalize quotes
        (r"[''']", "'", 0),                # Normalize apostrophes
        (r'(?<=[.!?])\n(?=[A-Z])', ' ', 0), # Join sentences across lines
        (r'\[.*?\]', '', 0),               # Remove editorial notes [sic] etc
        (r'\d{1,3}\s*$', '', re.MULTILINE), # Page numbers at end of lines
    ]
    
    # Iterate safely handling optional flags
    for item in ocr_fixes:
        pattern = item[0]
        replacement = item[1]
        flags = item[2] if len(item) > 2 else 0
        
        text = re.sub(pattern, replacement, text, flags=flags)
    
    # Remove very short lines (likely headers/footers)
    lines = text.split('\n')
    lines = [line for line in lines if len(line.strip()) > 20 or line.strip() == '']
    text = '\n'.join(lines)
    
    # Normalize old spellings (common ones)
    old_spellings = [
        (r'\bto-day\b', 'today'),
        (r'\bto-morrow\b', 'tomorrow'),
        (r'\bto-night\b', 'tonight'),
        (r'\b&\b', 'and'),
    ]
    
    for old, new in old_spellings:
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    
    return text.strip()


def extract_document_metadata(text: str, archive_metadata: Dict) -> Dict:
    """Extract key metadata from document"""
    
    metadata = {
        "archive_id": archive_metadata.get("identifier", "unknown"),
        "title": archive_metadata.get("title", "Untitled Document"),
        "creator": archive_metadata.get("creator", "Unknown"),
        "date": archive_metadata.get("date", "Unknown"),
        "description": archive_metadata.get("description", ""),
        "subjects": archive_metadata.get("subject", []),
        "word_count": len(text.split()) if text else 0,
        "year": None
    }
    
    # Try to extract year
    date_str = str(metadata["date"])
    year_match = re.search(r'\b(1[0-9]{3})\b', date_str)
    if year_match:
        metadata["year"] = int(year_match.group(1))
    
    return metadata


def split_text_for_duration(text: str, target_minutes: int, words_per_minute: int = 120) -> str:
    """Extract a portion of text for target duration"""
    
    target_words = target_minutes * words_per_minute
    words = text.split()
    
    if len(words) <= target_words:
        return text
    
    # Find a good break point near target
    target_text = ' '.join(words[:target_words])
    
    # Try to end at a sentence
    last_period = target_text.rfind('.')
    if last_period > len(target_text) * 0.8:  # If period is in last 20%
        target_text = target_text[:last_period + 1]
    
    return target_text


def select_random_document(
    document_type: str = None,
    min_words: int = 500,
    max_words: int = 50000
) -> Optional[Dict]:
    """Select a random document suitable for video creation"""
    
    # Random document type if not specified
    if not document_type:
        document_type = random.choice(list(DOCUMENT_TYPES.keys()))
    
    print(f"\n[DOCUMENT SCRAPER] Selecting random {document_type}")
    
    # Search for documents
    docs = search_internet_archive("", document_type, max_results=20)
    
    if not docs:
        print("  No documents found")
        return None
    
    # Shuffle and try to find suitable document
    random.shuffle(docs)
    
    for doc in docs[:10]:  # Try up to 10
        archive_id = doc.get("identifier")
        if not archive_id:
            continue
        
        # Get full text
        text = get_document_text(archive_id)
        if not text:
            continue
        
        # Clean text
        cleaned_text = clean_document_text(text)
        word_count = len(cleaned_text.split())
        
        # Check word count
        if word_count < min_words:
            print(f"  Skipping {archive_id}: too short ({word_count} words)")
            continue
        
        if word_count > max_words:
            print(f"  Document {archive_id} is long ({word_count} words), will truncate")
        
        # Get images
        images = get_document_images(archive_id, max_images=15)
        
        # Extract metadata
        metadata = extract_document_metadata(cleaned_text, doc)
        
        print(f"  ✓ Selected: {metadata['title'][:50]}...")
        print(f"    Words: {word_count}, Year: {metadata['year']}")
        
        return {
            "metadata": metadata,
            "text": cleaned_text,
            "images": images,
            "document_type": document_type
        }
    
    print("  No suitable documents found after trying 10")
    return None