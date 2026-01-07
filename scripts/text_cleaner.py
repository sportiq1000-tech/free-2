"""
Text Cleaner for The Bureaucratic Archivist
Uses Groq LLMs to clean and format Gutenberg text

Fixes:
- Hard wraps (70-char line breaks)
- Split paragraphs
- OCR artifacts
- Formatting issues
"""

import os
import requests
import re
from typing import Optional, Dict

# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Model for text cleaning (fast and capable)
CLEANER_MODEL = "llama-3.3-70b-versatile"


def call_groq(
    prompt: str,
    model: str = CLEANER_MODEL,
    api_key: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.1
) -> Optional[str]:
    """
    Make API call to Groq
    """
    
    key = api_key or GROQ_API_KEY
    
    if not key:
        print("  ❌ No Groq API key")
        return None
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"  ❌ Groq API error {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ❌ API call failed: {str(e)[:50]}")
        return None


def fix_hard_wraps(text: str) -> str:
    """
    Fix Gutenberg-style hard wraps (70-char line breaks)
    
    Before:
    "This is a sentence that was
    broken across multiple lines
    because of the 70 character
    limit in old text files."
    
    After:
    "This is a sentence that was broken across multiple 
    lines because of the 70 character limit in old text files."
    """
    
    lines = text.split('\n')
    result = []
    current_paragraph = []
    
    for line in lines:
        stripped = line.strip()
        
        # Empty line = paragraph break
        if not stripped:
            if current_paragraph:
                result.append(' '.join(current_paragraph))
                current_paragraph = []
            result.append('')
            continue
        
        # Check if this line continues previous
        # (doesn't start with capital after period, or is short)
        if current_paragraph:
            last_char = current_paragraph[-1][-1] if current_paragraph[-1] else ''
            
            # If previous line ended mid-sentence, join
            if last_char not in '.!?:' and not stripped[0].isupper():
                current_paragraph.append(stripped)
                continue
            
            # If previous line ended with sentence but this is continuation
            if len(stripped) > 50 and not stripped[0].isupper():
                current_paragraph.append(stripped)
                continue
        
        # Check if this is a heading (short, possibly all caps)
        if len(stripped) < 60 and (stripped.isupper() or stripped.endswith(':')):
            if current_paragraph:
                result.append(' '.join(current_paragraph))
                current_paragraph = []
            result.append(stripped)
            continue
        
        # Regular line - add to current paragraph
        current_paragraph.append(stripped)
    
    # Don't forget last paragraph
    if current_paragraph:
        result.append(' '.join(current_paragraph))
    
    return '\n\n'.join([p for p in result if p])


def clean_text_basic(text: str) -> str:
    """
    Basic regex-based cleaning (fast, no API)
    """
    
    # Fix multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Fix multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Fix common OCR errors
    text = text.replace(' ,', ',')
    text = text.replace(' .', '.')
    text = text.replace(' ;', ';')
    text = text.replace(' :', ':')
    text = text.replace(',,', ',')
    text = text.replace('..', '.')
    
    # Fix quotes
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"[''']", "'", text)
    
    # Normalize dashes
    text = re.sub(r'—|–', '-', text)
    
    return text.strip()


def clean_text_with_llm(
    text: str,
    api_key: str = None,
    chunk_size: int = 3000
) -> str:
    """
    Use LLM to intelligently clean and reformat text
    
    Processes in chunks to handle large documents
    """
    
    print("  🤖 Cleaning text with LLM...")
    
    # For short texts, process in one go
    if len(text) < chunk_size:
        return clean_single_chunk(text, api_key)
    
    # Split into chunks at paragraph boundaries
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        if current_size + len(para) > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(para)
        current_size += len(para)
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    print(f"  📄 Processing {len(chunks)} chunks...")
    
    # Process each chunk
    cleaned_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"     Chunk {i+1}/{len(chunks)}...")
        cleaned = clean_single_chunk(chunk, api_key)
        if cleaned:
            cleaned_chunks.append(cleaned)
        else:
            # Fallback to basic cleaning if LLM fails
            cleaned_chunks.append(clean_text_basic(fix_hard_wraps(chunk)))
    
    return '\n\n'.join(cleaned_chunks)


def clean_single_chunk(text: str, api_key: str = None) -> Optional[str]:
    """
    Clean a single chunk of text using LLM
    """
    
    prompt = f"""You are a text formatting expert. Clean and reformat this historical document text.

INPUT TEXT:
\"\"\"{text}\"\"\"

TASKS:
1. Fix hard wraps (join lines that were split at 70 characters)
2. Preserve paragraph breaks (double newlines)
3. Keep section headings on their own lines
4. Fix any obvious OCR errors or typos
5. Normalize spacing and punctuation
6. Keep archaic spellings (to-day, connexion, etc.) - these are authentic
7. Do NOT change the content or meaning

OUTPUT:
Return ONLY the cleaned text. No explanations, no markdown, just the reformatted text."""

    result = call_groq(prompt, api_key=api_key, max_tokens=4000)
    
    if result:
        # Remove any markdown formatting the LLM might have added
        result = re.sub(r'^```.*\n?', '', result)
        result = re.sub(r'\n?```$', '', result)
        return result.strip()
    
    return None


def clean_gutenberg_text(
    text: str,
    api_key: str = None,
    use_llm: bool = True
) -> Dict:
    """
    Main function: Clean Gutenberg text
    
    Args:
        text: Raw text from Gutenberg
        api_key: Groq API key (optional, uses env var)
        use_llm: Whether to use LLM cleaning (slower but better)
        
    Returns:
        {
            "cleaned_text": str,
            "word_count": int,
            "method": str
        }
    """
    
    print("\n[TEXT CLEANER]")
    
    original_words = len(text.split())
    print(f"  📄 Input: {len(text):,} chars, {original_words:,} words")
    
    # Step 1: Basic cleaning (always do this)
    text = clean_text_basic(text)
    
    # Step 2: Fix hard wraps
    text = fix_hard_wraps(text)
    
    # Step 3: LLM cleaning (optional but recommended)
    if use_llm and (api_key or GROQ_API_KEY):
        text = clean_text_with_llm(text, api_key)
        method = "LLM + regex"
    else:
        method = "regex only"
        print("  ⚠️ Skipping LLM cleaning (no API key or disabled)")
    
    # Final stats
    final_words = len(text.split())
    print(f"  ✅ Output: {len(text):,} chars, {final_words:,} words")
    print(f"  📊 Method: {method}")
    
    return {
        "cleaned_text": text,
        "word_count": final_words,
        "method": method
    }


def clean_for_narration(text: str, target_minutes: int = 10, api_key: str = None) -> Dict:
    """
    Main function: 
    1. Selects RAW chunk first
    2. Cleans in SAFE small batches to avoid truncation
    3. Trims to exact duration
    """
    
    print("\n[TEXT CLEANER - OPTIMIZED]")
    
    # Calculate target words (slow reading ~120 wpm)
    wpm = 120
    target_words = target_minutes * wpm
    print(f"  🎯 Target: {target_words} words ({target_minutes} mins)")
    
    # Step 1: Select RAW chunk
    raw_chunk = select_smart_chunk(text, target_words + 200) # Buffer
    print(f"  ✂️ Raw chunk size: {len(raw_chunk)} chars")
    
    final_text = ""
    
    # Step 2: Clean in safe batches (max 3000 chars per call)
    if api_key or GROQ_API_KEY:
        # Split raw chunk into smaller pieces to avoid truncation
        # 3000 chars is safe for 4096 token output limit
        batch_size = 3000
        
        # Split by paragraphs to keep context
        paragraphs = raw_chunk.split('\n\n')
        current_batch = []
        current_len = 0
        cleaned_parts = []
        
        print(f"  🔄 Splitting into safe batches...")
        
        for para in paragraphs:
            if current_len + len(para) > batch_size:
                # Process this batch
                batch_text = '\n\n'.join(current_batch)
                cleaned = clean_text_with_llm(batch_text, api_key)
                cleaned_parts.append(cleaned)
                
                # Reset
                current_batch = []
                current_len = 0
            
            current_batch.append(para)
            current_len += len(para)
        
        # Process final batch
        if current_batch:
            batch_text = '\n\n'.join(current_batch)
            cleaned = clean_text_with_llm(batch_text, api_key)
            cleaned_parts.append(cleaned)
            
        clean_chunk = '\n\n'.join(cleaned_parts)
    else:
        print("  ⚠️ No API key - using regex cleaning")
        clean_chunk = fix_hard_wraps(raw_chunk)
        
    # Step 3: Trim to exact length (ending on sentence)
    words = clean_chunk.split()
    
    if len(words) > target_words:
        trimmed = ' '.join(words[:target_words])
        
        # Find last sentence end
        last_period = trimmed.rfind('.')
        last_question = trimmed.rfind('?')
        last_exclaim = trimmed.rfind('!')
        
        last_sentence_end = max(last_period, last_question, last_exclaim)
        
        if last_sentence_end > len(trimmed) * 0.8:
            trimmed = trimmed[:last_sentence_end + 1]
            
        final_text = trimmed
    else:
        final_text = clean_chunk
        
    final_words = len(final_text.split())
    print(f"  ✅ Final text: {final_words} words")
    
    return {
        "text": final_text,
        "word_count": final_words,
        "estimated_minutes": final_words / wpm,
        "method": "LLM Batch Clean"
    }


# Test function
if __name__ == "__main__":
    # Test with sample Gutenberg-style text
    test_text = """
CHAPTER I.

INTRODUCTION.

All business should be brought before
the assembly by a motion of a member,
or by the presentation of a communi-
cation to the assembly. It is not usual
to make motions to receive reports of
committees or communications to the
assembly.

Motions are of two kinds, viz.: (1) Main
or principal motions, which bring busi-
ness before the assembly; and (2) Sec-
ondary motions, which may be made
while the main motion is pending.
"""
    
    print("=" * 70)
    print("Testing Text Cleaner")
    print("=" * 70)
    
    print("\nOriginal text:")
    print("-" * 40)
    print(test_text)
    
    # Test without LLM (regex only)
    print("\n" + "=" * 70)
    print("Testing basic cleaning (no LLM)...")
    result = clean_gutenberg_text(test_text, use_llm=False)
    
    print("\nCleaned text:")
    print("-" * 40)
    print(result["cleaned_text"])