"""
Document Scraper for The Bureaucratic Archivist
Enhanced with strict quality validation and copyright safety
"""

import os
import requests
import json
import random
import re
from datetime import datetime
from typing import Optional, Dict, List
import string

# Configuration
INTERNET_ARCHIVE_API = "https://archive.org/advancedsearch.php"

# Strict document type configurations (Pre-1928 only, narrative focus)
DOCUMENT_TYPES = {
    "ship_log": {
        "search_terms": [
            "ship log narrative", 
            "voyage journal", 
            "captain's journal",
            "maritime diary",
            "sea voyage log"
        ],
        "date_range": "1700-1927",  # Pre-1928 for safety
        "collections": ["americana", "naval", "maritime"],
        "priority": "high",
        "min_narrative_ratio": 0.6  # 60% should be narrative text
    },
    "government_report": {
        "search_terms": [
            "annual report",
            "commission report", 
            "department report",
            "official report"
        ],
        "date_range": "1800-1927",  # Pre-1928 for safety
        "collections": ["governmentpublications", "americana", "usfederalgovernmentpublications"],
        "priority": "high",
        "exclude_terms": ["statistical", "census", "table"]  # Avoid number-heavy docs
    }
}

# Quality thresholds (90%+ requirement)
QUALITY_THRESHOLDS = {
    "english_word_ratio": 0.90,      # 90% real English words
    "ascii_ratio": 0.95,              # 95% normal ASCII characters
    "avg_word_length": (3, 12),       # Words between 3-12 chars average
    "sentence_structure": 0.85,       # 85% of text has proper sentences
    "max_punctuation_ratio": 0.15     # No more than 15% punctuation
}


def search_internet_archive(
    query: str,
    document_type: str = "ship_log",
    max_results: int = 20
) -> List[Dict]:
    """Search Internet Archive with strict safety filters"""
    
    config = DOCUMENT_TYPES.get(document_type)
    if not config:
        print(f"  Unknown document type: {document_type}")
        return []
    
    # Build search query
    search_term = random.choice(config["search_terms"])
    if query:
        search_term = f"{search_term} {query}"
    
    # Add exclusions for government reports
    if "exclude_terms" in config:
        for term in config["exclude_terms"]:
            search_term += f" NOT {term}"
    
    year_range = config["date_range"]
    
    # Build query with collection filter for safety
    collections_filter = " OR ".join([f'collection:"{c}"' for c in config["collections"]])
    
    params = {
        "q": f"({search_term}) AND mediatype:texts AND year:[{year_range.replace('-', ' TO ')}] AND ({collections_filter})",
        "fl[]": ["identifier", "title", "creator", "date", "description", "subject", "collection"],
        "sort[]": "downloads desc",
        "rows": max_results,
        "page": 1,
        "output": "json"
    }
    
    try:
        print(f"  Searching Internet Archive: {search_term}")
        print(f"  Date range: {year_range} (Pre-1928 safety)")
        response = requests.get(INTERNET_ARCHIVE_API, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            print(f"  Found {len(docs)} candidates")
            return docs
        else:
            print(f"  Archive API error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  Archive search error: {e}")
        return []


def get_document_text(archive_id: str) -> Optional[str]:
    """Fetch full text from Internet Archive"""
    
    formats = [f"{archive_id}_djvu.txt", f"{archive_id}_text.txt", f"{archive_id}.txt"]
    
    for fmt in formats:
        text_url = f"https://archive.org/download/{archive_id}/{fmt}"
        try:
            response = requests.get(text_url, timeout=30)
            
            if response.status_code == 200:
                text = response.text
                if "<html" in text[:100].lower():
                    continue
                return text
        except:
            continue
            
    return None


def validate_text_quality(text: str, document_type: str = None) -> Dict:
    """
    Strict quality validation (90%+ threshold)
    Returns: {
        "passed": bool,
        "score": float,
        "details": dict,
        "reason": str
    }
    """
    
    if not text or len(text) < 500:
        return {
            "passed": False,
            "score": 0.0,
            "details": {},
            "reason": "Text too short (< 500 chars)"
        }
    
    # Load English word list (basic check)
    common_words = set([
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'ship', 'vessel', 'captain', 'voyage', 'sea', 'wind', 'day', 'port',
        'report', 'year', 'department', 'committee', 'act', 'law', 'state'
    ])
    
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    total_words = len(words)
    
    if total_words < 100:
        return {
            "passed": False,
            "score": 0.0,
            "details": {},
            "reason": "Too few words extracted (< 100)"
        }
    
    # 1. English Word Ratio
    english_words = sum(1 for w in words if w in common_words or len(w) > 2)
    english_ratio = english_words / total_words if total_words > 0 else 0
    
    # 2. ASCII Character Ratio
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    ascii_ratio = ascii_chars / len(text)
    
    # 3. Average Word Length
    avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
    word_len_ok = QUALITY_THRESHOLDS["avg_word_length"][0] <= avg_word_len <= QUALITY_THRESHOLDS["avg_word_length"][1]
    
    # 4. Sentence Structure (periods, capital letters)
    sentences = text.count('.')
    capitals = sum(1 for c in text if c.isupper())
    sentence_ratio = min(sentences / (total_words / 15), 1.0)  # ~15 words per sentence
    
    # 5. Punctuation Ratio (detect excessive symbols)
    punctuation_count = sum(1 for c in text if c in string.punctuation)
    punct_ratio = punctuation_count / len(text)
    
    # Calculate overall score
    scores = {
        "english_ratio": english_ratio,
        "ascii_ratio": ascii_ratio,
        "word_length_ok": 1.0 if word_len_ok else 0.0,
        "sentence_structure": sentence_ratio,
        "punctuation_ok": 1.0 if punct_ratio <= QUALITY_THRESHOLDS["max_punctuation_ratio"] else 0.0
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
    # Check against thresholds
    passed = (
        english_ratio >= QUALITY_THRESHOLDS["english_word_ratio"] and
        ascii_ratio >= QUALITY_THRESHOLDS["ascii_ratio"] and
        word_len_ok and
        sentence_ratio >= QUALITY_THRESHOLDS["sentence_structure"] and
        punct_ratio <= QUALITY_THRESHOLDS["max_punctuation_ratio"]
    )
    
    details = {
        "english_word_ratio": f"{english_ratio:.2%}",
        "ascii_ratio": f"{ascii_ratio:.2%}",
        "avg_word_length": f"{avg_word_len:.1f}",
        "sentence_structure": f"{sentence_ratio:.2%}",
        "punctuation_ratio": f"{punct_ratio:.2%}",
        "total_words": total_words
    }
    
    reason = "Passed all quality checks" if passed else "Failed: "
    if not passed:
        failures = []
        if english_ratio < QUALITY_THRESHOLDS["english_word_ratio"]:
            failures.append(f"Low English ratio ({english_ratio:.1%})")
        if ascii_ratio < QUALITY_THRESHOLDS["ascii_ratio"]:
            failures.append(f"Too many non-ASCII chars ({ascii_ratio:.1%})")
        if not word_len_ok:
            failures.append(f"Unusual word length ({avg_word_len:.1f})")
        if sentence_ratio < QUALITY_THRESHOLDS["sentence_structure"]:
            failures.append(f"Poor sentence structure ({sentence_ratio:.1%})")
        if punct_ratio > QUALITY_THRESHOLDS["max_punctuation_ratio"]:
            failures.append(f"Excessive punctuation ({punct_ratio:.1%})")
        reason += ", ".join(failures)
    
    return {
        "passed": passed,
        "score": overall_score,
        "details": details,
        "reason": reason
    }


def verify_copyright_safety(metadata: Dict) -> Dict:
    """
    Verify document is safely in public domain
    Returns: {
        "safe": bool,
        "reason": str,
        "confidence": str
    }
    """
    
    archive_id = metadata.get("identifier", "")
    date_str = str(metadata.get("date", ""))
    collections = metadata.get("collection", [])
    if isinstance(collections, str):
        collections = [collections]
    
    # Extract year
    year_match = re.search(r'\b(1[0-9]{3})\b', date_str)
    year = int(year_match.group(1)) if year_match else None
    
    # Check 1: Year must be pre-1928
    if not year or year >= 1928:
        return {
            "safe": False,
            "reason": f"Year {year} not safely in public domain (need pre-1928)",
            "confidence": "low"
        }
    
    # Check 2: Must be in trusted government collections
    trusted_collections = [
        "governmentpublications",
        "usfederalgovernmentpublications", 
        "americana",
        "naval",
        "maritime"
    ]
    
    in_trusted = any(tc in str(collections).lower() for tc in trusted_collections)
    
    if not in_trusted:
        return {
            "safe": False,
            "reason": f"Not in trusted government collection",
            "confidence": "medium"
        }
    
    return {
        "safe": True,
        "reason": f"Pre-1928 ({year}) + Government collection",
        "confidence": "high"
    }


def check_narrative_content(text: str, document_type: str) -> bool:
    """Check if document has enough narrative content (for ship logs)"""
    
    if document_type != "ship_log":
        return True  # Only check ship logs
    
    # Look for narrative indicators
    narrative_indicators = [
        r'\b(sailed|departed|arrived|encountered|observed|sighted)\b',
        r'\b(weather|wind|sea|waves|crew|captain)\b',
        r'\b(today|yesterday|morning|evening|night)\b',
        r'\b(we|our|the ship|vessel)\b'
    ]
    
    narrative_matches = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in narrative_indicators)
    total_words = len(text.split())
    
    narrative_ratio = narrative_matches / total_words if total_words > 0 else 0
    
    # Require 60% narrative content
    min_ratio = DOCUMENT_TYPES[document_type].get("min_narrative_ratio", 0.6)
    
    return narrative_ratio >= min_ratio


def clean_document_text(raw_text: str) -> str:
    """Clean OCR text - same as before"""
    
    if not raw_text:
        return ""
    
    text = raw_text
    
    # Clean up
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n([a-z])', r' \1', text)
    text = text.replace('|', 'I')
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"[''']", "'", text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    
    lines = text.split('\n')
    lines = [line for line in lines if len(line.strip()) > 20 or line.strip() == '']
    text = '\n'.join(lines)
    
    # Normalize old spellings
    old_spellings = [
        (r'\bto-day\b', 'today'),
        (r'\bto-morrow\b', 'tomorrow'),
        (r'\bto-night\b', 'tonight'),
        (r'\b&\b', 'and'),
    ]
    
    for old, new in old_spellings:
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    
    return text.strip()


def get_document_images(archive_id: str, max_images: int = 10) -> List[str]:
    """Get image URLs for document pages"""
    
    image_urls = []
    image_urls.append(f"https://archive.org/services/img/{archive_id}")
    
    base_url = f"https://archive.org/download/{archive_id}"
    
    for i in range(1, max_images + 1):
        image_urls.append(f"{base_url}/page/n{i}.jpg")
        pad = str(i).zfill(4)
        image_urls.append(f"{base_url}/{archive_id}_jp2/page_{pad}.jpg")
    
    return image_urls


def extract_document_metadata(text: str, archive_metadata: Dict) -> Dict:
    """Extract metadata - same as before"""
    
    metadata = {
        "archive_id": archive_metadata.get("identifier", "unknown"),
        "title": archive_metadata.get("title", "Untitled Document"),
        "creator": archive_metadata.get("creator", "Unknown"),
        "date": archive_metadata.get("date", "Unknown"),
        "description": archive_metadata.get("description", ""),
        "subjects": archive_metadata.get("subject", []),
        "collections": archive_metadata.get("collection", []),
        "word_count": len(text.split()) if text else 0,
        "year": None
    }
    
    date_str = str(metadata["date"])
    year_match = re.search(r'\b(1[0-9]{3})\b', date_str)
    if year_match:
        metadata["year"] = int(year_match.group(1))
    
    return metadata


def split_text_for_duration(text: str, target_minutes: int, words_per_minute: int = 120) -> str:
    """Extract portion of text for target duration"""
    
    target_words = target_minutes * words_per_minute
    words = text.split()
    
    if len(words) <= target_words:
        return text
    
    target_text = ' '.join(words[:target_words])
    last_period = target_text.rfind('.')
    if last_period > len(target_text) * 0.8:
        target_text = target_text[:last_period + 1]
    
    return target_text


def select_random_document(
    document_type: str = None,
    min_words: int = 800,
    max_words: int = 50000
) -> Optional[Dict]:
    """
    Select random document with STRICT quality & copyright validation
    Tries up to 10 documents, returns None if all fail
    """
    
    if not document_type:
        document_type = random.choice(list(DOCUMENT_TYPES.keys()))
    
    if document_type not in DOCUMENT_TYPES:
        print(f"\n[DOCUMENT SCRAPER] Error: Unknown type '{document_type}'")
        print(f"  Available: {list(DOCUMENT_TYPES.keys())}")
        return None
    
    print(f"\n[DOCUMENT SCRAPER] Selecting {document_type}")
    print(f"  Quality threshold: 90%+")
    print(f"  Copyright: Pre-1928 + Government sources only")
    
    docs = search_internet_archive("", document_type, max_results=20)
    
    if not docs:
        print("  ❌ No documents found in search")
        return None
    
    random.shuffle(docs)
    
    attempts = 0
    max_attempts = 10
    
    for doc in docs[:max_attempts]:
        attempts += 1
        archive_id = doc.get("identifier")
        
        if not archive_id:
            continue
        
        print(f"\n  📄 Attempt {attempts}/{max_attempts}: {doc.get('title', 'Untitled')[:50]}...")
        
        # Check copyright safety FIRST (before downloading)
        copyright_check = verify_copyright_safety(doc)
        if not copyright_check["safe"]:
            print(f"     ❌ Copyright: {copyright_check['reason']}")
            continue
        else:
            print(f"     ✅ Copyright: {copyright_check['reason']}")
        
        # Get text
        text = get_document_text(archive_id)
        if not text:
            print(f"     ❌ No text available")
            continue
        
        # Clean text
        cleaned_text = clean_document_text(text)
        word_count = len(cleaned_text.split())
        
        # Check word count
        if word_count < min_words:
            print(f"     ❌ Too short: {word_count} words (need {min_words}+)")
            continue
        
        # Validate quality
        quality = validate_text_quality(cleaned_text, document_type)
        print(f"     📊 Quality score: {quality['score']:.1%}")
        
        if not quality["passed"]:
            print(f"     ❌ Quality: {quality['reason']}")
            for key, value in quality["details"].items():
                print(f"        - {key}: {value}")
            continue
        else:
            print(f"     ✅ Quality: {quality['reason']}")
        
        # Check narrative content (ship logs only)
        if document_type == "ship_log":
            has_narrative = check_narrative_content(cleaned_text, document_type)
            if not has_narrative:
                print(f"     ❌ Insufficient narrative content")
                continue
            else:
                print(f"     ✅ Good narrative content")
        
        # All checks passed!
        images = get_document_images(archive_id, max_images=15)
        metadata = extract_document_metadata(cleaned_text, doc)
        
        print(f"\n  ✅ SELECTED!")
        print(f"     Title: {metadata['title'][:60]}")
        print(f"     Year: {metadata['year']}")
        print(f"     Words: {word_count}")
        print(f"     Quality: {quality['score']:.1%}")
        
        return {
            "metadata": metadata,
            "text": cleaned_text,
            "images": images,
            "document_type": document_type,
            "quality_score": quality["score"],
            "quality_details": quality["details"]
        }
    
    # All attempts failed
    print(f"\n  ❌ FAILED: Tried {attempts} documents, none met quality standards")
    print(f"     Suggestion: Try a different document type or run again")
    
    return None