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
WIKISOURCE_API = "https://en.wikisource.org/w/api.php"

# Document type configurations
DOCUMENT_TYPES = {
    "maritime_log": {
        "search_terms": ["ship log", "maritime log", "captain's log", "voyage journal", "naval log"],
        "date_range": "1700-1920",
        "collections": ["americana", "naval", "maritime"]
    },
    "patent": {
        "search_terms": ["patent", "invention", "patent drawing"],
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
    """
    Search Internet Archive for documents
    
    Args:
        query: Additional search terms
        document_type: Type of document to search for
        max_results: Maximum number of results
    
    Returns:
        List of document metadata dictionaries
    """
    
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
    """
    Fetch full text of a document from Internet Archive
    
    Args:
        archive_id: Internet Archive identifier
    
    Returns:
        Document text or None if not available
    """
    
    # Try to get the text file directly
    text_url = f"https://archive.org/download/{archive_id}/{archive_id}_djvu.txt"
    
    try:
        print(f"  Fetching document text: {archive_id}")
        response = requests.get(text_url, timeout=60)
        
        if response.status_code == 200:
            text = response.text
            print(f"  Retrieved {len(text)} characters")
            return text
        else:
            # Try alternative format
            alt_url = f"https://archive.org/stream/{archive_id}/{archive_id}_djvu.txt"
            response = requests.get(alt_url, timeout=60)
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"  Text not available for {archive_id}")
                return None
                
    except Exception as e:
        print(f"  Error fetching text: {e}")
        return None


def get_document_images(archive_id: str, max_images: int = 10) -> List[str]:
    """
    Get image URLs for document pages
    
    Args:
        archive_id: Internet Archive identifier
        max_images: Maximum number of images to return
    
    Returns:
        List of image URLs
    """
    
    # Internet Archive page image URL pattern
    base_url = f"https://archive.org/download/{archive_id}/page"
    
    image_urls = []
    
    # Try to get page images
    for i in range(1, max_images + 1):
        # Common page naming patterns
        patterns = [
            f"n{i:04d}.jpg",
            f"n{i:03d}.jpg", 
            f"page{i:04d}.jpg",
            f"page{i:03d}.jpg"
        ]
        
        for pattern in patterns:
            url = f"https://archive.org/download/{archive_id}/{archive_id}_{pattern}"
            try:
                # Quick head request to check if exists
                resp = requests.head(url, timeout=5)
                if resp.status_code == 200:
                    image_urls.append(url)
                    break
            except:
                continue
        
        if len(image_urls) >= max_images:
            break
    
    # Fallback: Use the item thumbnail/preview
    if not image_urls:
        thumbnail = f"https://archive.org/services/img/{archive_id}"
        image_urls.append(thumbnail)
    
    print(f"  Found {len(image_urls)} document images")
    return image_urls


def clean_document_text(raw_text: str) -> str:
    """
    Clean OCR text from historical documents
    
    Args:
        raw_text: Raw OCR text
    
    Returns:
        Cleaned text suitable for narration
    """
    
    if not raw_text:
        return ""
    
    text = raw_text
    
    # Remove common OCR artifacts
    ocr_fixes = [
        (r'\n{3,}', '\n\n'),           # Multiple newlines to double
        (r'[ \t]+', ' '),               # Multiple spaces to single
        (r'-\n', ''),                   # Hyphenated line breaks
        (r'\n([a-z])', r' \1'),         # Join broken sentences
        (r'[|]', 'I'),                  # Common OCR error: | for I
        (r'(?<=[a-z])0(?=[a-z])', 'o'), # 0 for o in words
        (r'(?<=[a-z])1(?=[a-z])', 'l'), # 1 for l in words
        (r'["""]', '"'),                # Normalize quotes
        (r"[''']", "'"),                # Normalize apostrophes
        (r'(?<=[.!?])\n(?=[A-Z])', ' '), # Join sentences across lines
        (r'\[.*?\]', ''),               # Remove editorial notes [sic] etc
        (r'\d{1,3}\s*$', '', re.MULTILINE), # Page numbers at end of lines
    ]
    
    for pattern, replacement in ocr_fixes:
        if len(ocr_fixes[0]) == 2:
            text = re.sub(pattern, replacement, text)
        else:
            text = re.sub(pattern, replacement, text, flags=ocr_fixes[0][2] if len(ocr_fixes[0]) > 2 else 0)
    
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
    
    # Final cleanup
    text = text.strip()
    
    return text


def extract_document_metadata(text: str, archive_metadata: Dict) -> Dict:
    """
    Extract key metadata from document
    
    Args:
        text: Document text
        archive_metadata: Metadata from Internet Archive
    
    Returns:
        Structured metadata dictionary
    """
    
    metadata = {
        "archive_id": archive_metadata.get("identifier", "unknown"),
        "title": archive_metadata.get("title", "Untitled Document"),
        "creator": archive_metadata.get("creator", "Unknown"),
        "date": archive_metadata.get("date", "Unknown"),
        "description": archive_metadata.get("description", ""),
        "subjects": archive_metadata.get("subject", []),
        "word_count": len(text.split()) if text else 0,
        "char_count": len(text) if text else 0,
        "estimated_duration_minutes": round(len(text.split()) / 130) if text else 0  # ~130 wpm for slow reading
    }
    
    # Try to extract year
    date_str = str(metadata["date"])
    year_match = re.search(r'\b(1[0-9]{3})\b', date_str)
    if year_match:
        metadata["year"] = int(year_match.group(1))
    else:
        metadata["year"] = None
    
    return metadata


def split_text_for_duration(text: str, target_minutes: int, words_per_minute: int = 120) -> str:
    """
    Extract a portion of text for target duration
    
    Args:
        text: Full document text
        target_minutes: Target video duration in minutes
        words_per_minute: Reading speed (slower for sleep content)
    
    Returns:
        Text portion for target duration
    """
    
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
    min_words: int = 1000,
    max_words: int = 50000
) -> Optional[Dict]:
    """
    Select a random document suitable for video creation
    
    Args:
        document_type: Type of document (None for random)
        min_words: Minimum word count
        max_words: Maximum word count
    
    Returns:
        Document data dictionary or None
    """
    
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
        print(f"    Words: {word_count}, Est. duration: {metadata['estimated_duration_minutes']} min")
        
        return {
            "metadata": metadata,
            "text": cleaned_text,
            "images": images,
            "document_type": document_type
        }
    
    print("  No suitable documents found after trying 10")
    return None


# For testing
if __name__ == "__main__":
    print("Testing document scraper...")
    doc = select_random_document("maritime_log", min_words=500)
    if doc:
        print(f"\nDocument: {doc['metadata']['title']}")
        print(f"Year: {doc['metadata']['year']}")
        print(f"Words: {doc['metadata']['word_count']}")
        print(f"Images: {len(doc['images'])}")
        print(f"\nFirst 500 chars:\n{doc['text'][:500]}")