"""
Document Scraper for The Bureaucratic Archivist
Enhanced with strict quality validation, copyright safety, and new document types
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

# Enhanced document types (Pre-1928 only, bureaucratic focus)
DOCUMENT_TYPES = {
    "government_report": {
        "search_terms": [
            "annual report",
            "commission report", 
            "department report",
            "official report",
            "bureau report"
        ],
        "date_range": "1800-1927",
        "collections": ["governmentpublications", "americana", "usfederalgovernmentpublications"],
        "priority": "high",
        "exclude_terms": ["statistical table", "census table"]
    },
    "postal_regulations": {
        "search_terms": [
            "postal laws and regulations",
            "post office regulations",
            "postal service rules",
            "mail regulations"
        ],
        "date_range": "1800-1927",
        "collections": ["governmentpublications", "usfederalgovernmentpublications"],
        "priority": "high"
    },
    "civil_service": {
        "search_terms": [
            "civil service commission",
            "civil service report",
            "civil service examination",
            "government employment"
        ],
        "date_range": "1850-1927",
        "collections": ["governmentpublications", "usfederalgovernmentpublications"],
        "priority": "high"
    },
    "style_manual": {
        "search_terms": [
            "government printing office style",
            "GPO style manual",
            "manual of style",
            "printing office manual"
        ],
        "date_range": "1880-1927",
        "collections": ["governmentpublications"],
        "priority": "medium"
    },
    "city_ordinance": {
        "search_terms": [
            "city ordinance",
            "municipal ordinance",
            "town ordinance",
            "city code"
        ],
        "date_range": "1800-1927",
        "collections": ["americana", "governmentpublications"],
        "priority": "high"
    },
    "court_record": {
        "search_terms": [
            "court proceedings",
            "legal proceedings",
            "supreme court",
            "court decisions"
        ],
        "date_range": "1800-1927",
        "collections": ["americana", "usfederalgovernmentpublications"],
        "priority": "medium"
    }
}

# Quality thresholds (90%+ requirement)
QUALITY_THRESHOLDS = {
    "english_word_ratio": 0.90,
    "ascii_ratio": 0.95,
    "avg_word_length": (3, 12),
    "sentence_structure": 0.50,  # Relaxed for historical long sentences
    "max_punctuation_ratio": 0.15
}


def search_internet_archive(
    query: str,
    document_type: str = "government_report",
    max_results: int = 20
) -> List[Dict]:
    """Search Internet Archive with strict safety filters"""
    
    config = DOCUMENT_TYPES.get(document_type)
    if not config:
        print(f"  Unknown document type: {document_type}")
        return []
    
    search_term = random.choice(config["search_terms"])
    if query:
        search_term = f"{search_term} {query}"
    
    if "exclude_terms" in config:
        for term in config["exclude_terms"]:
            search_term += f" NOT {term}"
    
    year_range = config["date_range"]
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


def skip_document_headers(text: str) -> str:
    """
    Skip Internet Archive metadata, table of contents, and decorative title pages
    Finds where actual narrative content begins
    """
    
    if len(text) < 10000:
        return text  # Too short to have meaningful headers
    
    # Strategy: Look for first substantial paragraph after char 3000
    potential_starts = []
    
    for i in range(3000, min(15000, len(text) - 1000)):
        # Look for paragraph start (double newline + capital)
        if text[i:i+2] == '\n\n' and i+2 < len(text) and text[i+2].isupper():
            next_section = text[i:i+300]
            
            # Count sentences (periods)
            periods = next_section.count('.')
            
            # Count actual words (not symbols)
            words = re.findall(r'\b[a-zA-Z]{3,}\b', next_section)
            
            # If it has sentences and real words, likely content
            if periods >= 2 and len(words) >= 20:
                potential_starts.append(i)
                if len(potential_starts) >= 3:
                    break
    
    # Use first good start, or fallback to char 5000
    if potential_starts:
        start = potential_starts[0]
        print(f"  Skipped {start:,} header characters")
        return text[start:]
    else:
        print(f"  Skipped 5,000 header characters (fallback)")
        return text[5000:] if len(text) > 5000 else text


def clean_document_text(raw_text: str) -> str:
    """Clean OCR text and skip headers"""
    
    if not raw_text:
        return ""
    
    # STEP 1: Skip headers/metadata
    text = skip_document_headers(raw_text)
    
    # STEP 2: Clean OCR artifacts
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'\n([a-z])', r' \1', text)
    text = text.replace('|', 'I')
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"[''']", "'", text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    
    # STEP 3: Remove short lines
    lines = text.split('\n')
    lines = [line for line in lines if len(line.strip()) > 20 or line.strip() == '']
    text = '\n'.join(lines)
    
    # STEP 4: Normalize old spellings
    old_spellings = [
        (r'\bto-day\b', 'today'),
        (r'\bto-morrow\b', 'tomorrow'),
        (r'\bto-night\b', 'tonight'),
        (r'\b&\b', 'and'),
    ]
    
    for old, new in old_spellings:
        text = re.sub(old, new, text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_text_quality(text: str, document_type: str = None) -> Dict:
    """Strict quality validation (90%+ threshold)"""
    
    if not text or len(text) < 500:
        return {
            "passed": False,
            "score": 0.0,
            "details": {},
            "reason": "Text too short (< 500 chars)"
        }
    
    common_words = set([
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
        'government', 'department', 'report', 'year', 'state', 'city', 'law'
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
    
    # Quality checks
    english_words = sum(1 for w in words if w in common_words or len(w) > 2)
    english_ratio = english_words / total_words if total_words > 0 else 0
    
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    ascii_ratio = ascii_chars / len(text)
    
    avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
    word_len_ok = QUALITY_THRESHOLDS["avg_word_length"][0] <= avg_word_len <= QUALITY_THRESHOLDS["avg_word_length"][1]
    
    sentences = text.count('.')
    sentence_ratio = min(sentences / (total_words / 15), 1.0)
    
    punctuation_count = sum(1 for c in text if c in string.punctuation)
    punct_ratio = punctuation_count / len(text)
    
    scores = {
        "english_ratio": english_ratio,
        "ascii_ratio": ascii_ratio,
        "word_length_ok": 1.0 if word_len_ok else 0.0,
        "sentence_structure": sentence_ratio,
        "punctuation_ok": 1.0 if punct_ratio <= QUALITY_THRESHOLDS["max_punctuation_ratio"] else 0.0
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
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
            failures.append(f"Too many non-ASCII ({ascii_ratio:.1%})")
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
    """Verify document is safely in public domain"""
    
    date_str = str(metadata.get("date", ""))
    collections = metadata.get("collection", [])
    if isinstance(collections, str):
        collections = [collections]
    
    year_match = re.search(r'\b(1[0-9]{3})\b', date_str)
    year = int(year_match.group(1)) if year_match else None
    
    if not year or year >= 1928:
        return {
            "safe": False,
            "reason": f"Year {year} not safely in public domain (need pre-1928)",
            "confidence": "low"
        }
    
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
    """Extract metadata"""
    
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
    """Select random document with STRICT quality & copyright validation"""
    
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
        
        copyright_check = verify_copyright_safety(doc)
        if not copyright_check["safe"]:
            print(f"     ❌ Copyright: {copyright_check['reason']}")
            continue
        else:
            print(f"     ✅ Copyright: {copyright_check['reason']}")
        
        text = get_document_text(archive_id)
        if not text:
            print(f"     ❌ No text available")
            continue
        
        cleaned_text = clean_document_text(text)
        word_count = len(cleaned_text.split())
        
        if word_count < min_words:
            print(f"     ❌ Too short: {word_count} words (need {min_words}+)")
            continue
        
        quality = validate_text_quality(cleaned_text, document_type)
        print(f"     📊 Quality score: {quality['score']:.1%}")
        
        if not quality["passed"]:
            print(f"     ❌ Quality: {quality['reason']}")
            continue
        else:
            print(f"     ✅ Quality: {quality['reason']}")
        
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
    
    print(f"\n  ❌ FAILED: Tried {attempts} documents, none met quality standards")
    print(f"     Suggestion: Try a different document type or run again")
    
    return None