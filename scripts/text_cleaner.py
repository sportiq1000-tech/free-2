"""
Text Cleaner for The Bureaucratic Archivist
Optimized for Groq Rate Limits
ONLY cleans the specific chunk needed for narration
"""

import os
import requests
import re
import random
from typing import Optional, Dict

# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
# Use versatile model which has reasonable limits (12k TPM / 30 RPM)
CLEANER_MODEL = "llama-3.3-70b-versatile"


def call_groq(
    prompt: str,
    model: str = CLEANER_MODEL,
    api_key: str = None,
    max_tokens: int = 4000
) -> Optional[str]:
    """
    Make API call to Groq with error handling
    """
    
    key = api_key or GROQ_API_KEY
    
    if not key:
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
                "temperature": 0.1,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"  ❌ Groq API Error {response.status_code}: {response.text[:100]}")
            return None
            
    except Exception as e:
        print(f"  ❌ API call failed: {str(e)[:50]}")
        return None


def fix_hard_wraps(text: str) -> str:
    """
    Fix Gutenberg-style hard wraps (regex only fallback)
    Joins lines that shouldn't be split
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
        
        # Heuristic for joining lines
        if current_paragraph:
            # Check if this looks like a new paragraph (e.g. indentation or chapter start)
            if len(stripped) < 50 and stripped.isupper():
                # Heading
                result.append(' '.join(current_paragraph))
                current_paragraph = []
                result.append(stripped)
                continue
                
            current_paragraph.append(stripped)
        else:
            current_paragraph.append(stripped)
            
    if current_paragraph:
        result.append(' '.join(current_paragraph))
        
    return '\n'.join(result)


def clean_text_with_llm(text: str, api_key: str = None) -> str:
    """
    Clean a specific text chunk using LLM
    """
    print(f"  🤖 Cleaning chunk ({len(text)} chars) with LLM...")
    
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

    result = call_groq(prompt, api_key=api_key)
    
    if result:
        # Remove any markdown formatting
        result = re.sub(r'^```.*\n?', '', result)
        result = re.sub(r'\n?```$', '', result)
        return result.strip()
        
    return text  # Return original if failed


def clean_gutenberg_text(text: str, api_key: str = None, use_llm: bool = True) -> Dict:
    """
    Simple wrapper for compatibility
    Just does basic regex cleaning on full text
    """
    cleaned = fix_hard_wraps(text)
    return {
        "cleaned_text": cleaned,
        "word_count": len(cleaned.split()),
        "method": "regex"
    }


def select_smart_chunk(text: str, target_words: int) -> str:
    """
    Select a contiguous chunk of text from the middle of the document
    Avoids headers/footers by skipping first/last 10%
    """
    
    words = text.split()
    total_words = len(words)
    
    if total_words <= target_words:
        return text
    
    # Define safe zone (middle 80%)
    start_buffer = int(total_words * 0.1)
    end_buffer = int(total_words * 0.9) - target_words
    
    if start_buffer < end_buffer:
        # Pick random start point in safe zone
        start_idx = random.randint(start_buffer, end_buffer)
    else:
        start_idx = 0
        
    # Extract chunk with some buffer
    chunk_words = words[start_idx : start_idx + target_words + 200]
    return ' '.join(chunk_words)


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
    print("Testing Text Cleaner...")
    sample = "This is a test text.\nIt has hard wraps.\nLike this."
    result = clean_for_narration(sample, target_minutes=1)
    print(f"Result: {result['text']}")