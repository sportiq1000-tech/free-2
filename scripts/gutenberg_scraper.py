"""
Project Gutenberg Scraper for The Bureaucratic Archivist
Fetches public domain documents - 100% copyright safe

Content types:
- Robert's Rules of Order (parliamentary procedure)
- Government manuals and regulations
- Old instruction manuals
- Legal texts and procedures
"""

import os
import requests
import random
import re
from typing import Optional, Dict, List

# Gutenberg mirror (reliable)
GUTENBERG_BASE = "https://www.gutenberg.org"
GUTENBERG_CACHE = "https://www.gutenberg.org/cache/epub"

# Curated list of PERFECT bureaucratic documents
# These are hand-picked for sleep/archival content
CURATED_DOCUMENTS = {
    "parliamentary": [
        {
            "id": 9097,
            "title": "Robert's Rules of Order",
            "author": "Henry M. Robert",
            "year": 1876,
            "description": "Parliamentary procedure manual"
        },
        {
            "id": 9098,
            "title": "Robert's Rules of Order Revised",
            "author": "Henry M. Robert", 
            "year": 1915,
            "description": "Updated parliamentary procedure"
        }
    ],
    "government": [
        {
            "id": 5983,
            "title": "The Constitution of the United States",
            "author": "Founding Fathers",
            "year": 1787,
            "description": "US Constitution full text"
        },
        {
            "id": 1656,
            "title": "The Federalist Papers",
            "author": "Hamilton, Madison, Jay",
            "year": 1788,
            "description": "Essays on the Constitution"
        }
    ],
    "legal": [
        {
            "id": 10700,
            "title": "Erta Act for Regulating of Printing",
            "author": "English Parliament",
            "year": 1662,
            "description": "Early printing regulations"
        }
    ],
    "manuals": [
        {
            "id": 17396,
            "title": "The American Frugal Housewife",
            "author": "Lydia Maria Child",
            "year": 1832,
            "description": "Household economy manual"
        },
        {
            "id": 22135,
            "title": "Practical Carriage Building",
            "author": "M.T. Richardson",
            "year": 1892,
            "description": "Technical manufacturing manual"
        },
        {
            "id": 19198,
            "title": "The Art of Letter Writing",
            "author": "Anonymous",
            "year": 1900,
            "description": "Correspondence etiquette"
        }
    ],
    "reports": [
        {
            "id": 10611,
            "title": "Scientific American Reference Book",
            "author": "Various",
            "year": 1905,
            "description": "Technical reference compilation"
        }
    ]
}


def get_gutenberg_text(book_id: int) -> Optional[str]:
    """
    Fetch plain text from Project Gutenberg
    
    Args:
        book_id: Gutenberg book ID number
        
    Returns:
        Raw text content or None if failed
    """
    
    # Try multiple URL formats (Gutenberg has several)
    url_formats = [
        f"{GUTENBERG_CACHE}/{book_id}/pg{book_id}.txt",
        f"{GUTENBERG_CACHE}/{book_id}/{book_id}.txt",
        f"{GUTENBERG_CACHE}/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
    ]
    
    headers = {
        'User-Agent': 'BureaucraticArchivist/1.0 (Educational Project)'
    }
    
    for url in url_formats:
        try:
            print(f"  Trying: {url[:60]}...")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                text = response.text
                
                # Verify it's actual text (not HTML error page)
                if len(text) > 1000 and '<html' not in text.lower()[:500]:
                    print(f"  ✅ Downloaded {len(text):,} characters")
                    return text
                    
        except Exception as e:
            continue
    
    print(f"  ❌ Could not fetch book {book_id}")
    return None


def strip_gutenberg_header_footer(text: str) -> str:
    """
    Remove Project Gutenberg header and footer boilerplate
    
    Gutenberg texts have standard markers:
    - "*** START OF THE PROJECT GUTENBERG EBOOK ***"
    - "*** END OF THE PROJECT GUTENBERG EBOOK ***"
    """
    
    # Find start marker
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG EBOOK",
        "*** START OF THIS PROJECT GUTENBERG EBOOK",
        "*END*THE SMALL PRINT",
        "***START OF THE PROJECT GUTENBERG",
    ]
    
    start_pos = 0
    for marker in start_markers:
        pos = text.upper().find(marker.upper())
        if pos != -1:
            # Find end of that line
            line_end = text.find('\n', pos)
            if line_end != -1:
                start_pos = line_end + 1
                break
    
    # Find end marker
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG EBOOK",
        "*** END OF THIS PROJECT GUTENBERG EBOOK",
        "***END OF THE PROJECT GUTENBERG",
        "End of the Project Gutenberg",
        "End of Project Gutenberg",
    ]
    
    end_pos = len(text)
    for marker in end_markers:
        pos = text.upper().find(marker.upper())
        if pos != -1:
            end_pos = pos
            break
    
    # Extract content
    content = text[start_pos:end_pos].strip()
    
    # Additional cleanup: remove "Produced by" lines at start
    lines = content.split('\n')
    clean_lines = []
    skip_header = True
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if skip_header:
            # Skip common Gutenberg production notes
            if any(phrase in line_lower for phrase in [
                'produced by',
                'transcribed by',
                'prepared by',
                'scanned by',
                'proofread by',
                'e-text prepared',
                'this etext',
                'this e-text',
                'online distributed',
                'proofreading team'
            ]):
                continue
            
            # Skip empty lines at start
            if not line.strip():
                continue
            
            # Found real content
            skip_header = False
        
        clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def search_gutenberg(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search Gutenberg catalog (uses their search API)
    
    Note: Gutenberg's search is limited. We primarily use curated list.
    This is a fallback for finding additional content.
    """
    
    # Gutenberg doesn't have a great API, so we'll use curated list
    # This function is for future expansion
    
    print(f"  Note: Using curated document list (Gutenberg search limited)")
    return []


def get_random_curated_document(category: str = None) -> Optional[Dict]:
    """
    Get a random document from our curated list
    
    Args:
        category: 'parliamentary', 'government', 'legal', 'manuals', 'reports'
                 or None for random category
    
    Returns:
        Document metadata dict
    """
    
    if category and category in CURATED_DOCUMENTS:
        docs = CURATED_DOCUMENTS[category]
    else:
        # Flatten all categories
        all_docs = []
        for cat_docs in CURATED_DOCUMENTS.values():
            all_docs.extend(cat_docs)
        docs = all_docs
    
    if not docs:
        return None
    
    return random.choice(docs)


def fetch_gutenberg_document(
    category: str = None,
    book_id: int = None
) -> Optional[Dict]:
    """
    Fetch a document from Project Gutenberg
    
    Args:
        category: Document category (or None for random)
        book_id: Specific book ID (overrides category)
        
    Returns:
        {
            "metadata": {...},
            "raw_text": str,
            "clean_text": str (header/footer stripped),
            "source": "gutenberg"
        }
    """
    
    print(f"\n[GUTENBERG SCRAPER]")
    
    # Get document info
    if book_id:
        # Find in curated list
        doc_info = None
        for cat_docs in CURATED_DOCUMENTS.values():
            for doc in cat_docs:
                if doc['id'] == book_id:
                    doc_info = doc
                    break
        
        if not doc_info:
            doc_info = {
                "id": book_id,
                "title": f"Gutenberg Book #{book_id}",
                "author": "Unknown",
                "year": None,
                "description": ""
            }
    else:
        doc_info = get_random_curated_document(category)
        if not doc_info:
            print("  ❌ No documents found in category")
            return None
    
    print(f"  📚 Fetching: {doc_info['title']}")
    print(f"     Author: {doc_info['author']}")
    print(f"     Year: {doc_info['year']}")
    print(f"     ID: {doc_info['id']}")
    
    # Fetch text
    raw_text = get_gutenberg_text(doc_info['id'])
    
    if not raw_text:
        return None
    
    # Strip Gutenberg boilerplate
    clean_text = strip_gutenberg_header_footer(raw_text)
    
    print(f"  📄 Raw: {len(raw_text):,} chars → Clean: {len(clean_text):,} chars")
    
    # Calculate word count
    word_count = len(clean_text.split())
    print(f"  📊 Words: {word_count:,}")
    
    return {
        "metadata": {
            "archive_id": f"gutenberg_{doc_info['id']}",
            "title": doc_info['title'],
            "creator": doc_info['author'],
            "year": doc_info['year'],
            "description": doc_info['description'],
            "word_count": word_count,
            "source": "Project Gutenberg",
            "copyright": "Public Domain"
        },
        "raw_text": raw_text,
        "text": clean_text,
        "source": "gutenberg"
    }


def list_available_categories() -> Dict:
    """List all available document categories"""
    
    result = {}
    for category, docs in CURATED_DOCUMENTS.items():
        result[category] = {
            "count": len(docs),
            "titles": [d['title'] for d in docs]
        }
    return result


def list_all_documents() -> List[Dict]:
    """List all curated documents"""
    
    all_docs = []
    for category, docs in CURATED_DOCUMENTS.items():
        for doc in docs:
            doc_copy = doc.copy()
            doc_copy['category'] = category
            all_docs.append(doc_copy)
    return all_docs


# Test function
if __name__ == "__main__":
    print("=" * 70)
    print("Testing Gutenberg Scraper")
    print("=" * 70)
    
    # List categories
    print("\n📁 Available Categories:")
    for cat, info in list_available_categories().items():
        print(f"   {cat}: {info['count']} documents")
    
    # Test fetch
    print("\n" + "=" * 70)
    doc = fetch_gutenberg_document(category='parliamentary')
    
    if doc:
        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print(f"Title: {doc['metadata']['title']}")
        print(f"Words: {doc['metadata']['word_count']}")
        print("\nFirst 500 characters:")
        print("-" * 70)
        print(doc['text'][:500])
        print("-" * 70)