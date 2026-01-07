"""
Script Enhancer for The Bureaucratic Archivist
Transforms raw documents into engaging "Researcher" scripts with modern comparisons
"""

import os
import json
import random

# Get API key from environment
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Curator persona templates
CURATOR_PERSONAS = [
    {
        "name": "The Scholarly Archivist",
        "style": "academic, precise, quietly passionate about history",
        "intro_tone": "measured and thoughtful"
    },
    {
        "name": "The Late-Night Curator",
        "style": "calm, slightly tired, intimate like sharing secrets",
        "intro_tone": "soft and contemplative"
    },
    {
        "name": "The Documentary Narrator",
        "style": "authoritative but warm, like a BBC documentary",
        "intro_tone": "professional yet approachable"
    }
]


def generate_curator_intro(
    document_metadata: dict,
    document_type: str,
    groq_api_key: str = None
) -> str:
    """
    Generate a unique curator's introduction explaining why this document matters
    
    This is the "Value Add" that YouTube requires for monetization
    """
    
    import requests
    
    api_key = groq_api_key or GROQ_API_KEY
    
    persona = random.choice(CURATOR_PERSONAS)
    
    prompt = f"""You are "{persona['name']}" - a {persona['style']} curator of historical documents.

Write a 60-90 second introduction (about 150-200 words) for a video reading of this document:

Document Title: {document_metadata.get('title', 'Unknown')}
Document Type: {document_type}
Year: {document_metadata.get('year', 'Unknown')}
Creator/Author: {document_metadata.get('creator', 'Unknown')}

Your introduction must:
1. Welcome the viewer warmly (vary this - don't always say "welcome back")
2. Explain WHAT this document is (be specific)
3. Explain WHY it matters historically
4. Add ONE modern comparison or relevance (e.g., "The logic used here is still found in...")
5. Set the mood for a calm, contemplative reading
6. End with a gentle transition into the document reading

Tone: {persona['intro_tone']}

Write ONLY the introduction script. No stage directions, no [brackets], just the words to be spoken.

Begin:"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a thoughtful museum curator who makes history accessible and engaging."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            intro = response.json()["choices"][0]["message"]["content"]
            return intro.strip()
        else:
            print(f"  Groq API error: {response.status_code}")
            return generate_fallback_intro(document_metadata, document_type)
            
    except Exception as e:
        print(f"  Intro generation error: {e}")
        return generate_fallback_intro(document_metadata, document_type)


def generate_fallback_intro(metadata: dict, doc_type: str) -> str:
    """Generate a simple intro if API fails"""
    
    intros = [
        f"Tonight, we turn our attention to a remarkable {doc_type} from {metadata.get('year', 'history')}. {metadata.get('title', 'This document')} offers us a window into a world that, while distant, still echoes in our own time. Let us begin.",
        
        f"In the quiet hours, we return to the archives. Before us lies {metadata.get('title', 'a document')} from {metadata.get('year', 'the past')}. As we read these words, remember that someone once wrote them by candlelight, never imagining we would hear them today. Let us listen.",
        
        f"Welcome to the archive. This {doc_type}, dated {metadata.get('year', 'from years past')}, has waited patiently for someone to read it again. Tonight, that someone is us. The document before us is {metadata.get('title', 'quite fascinating')}. Shall we begin?"
    ]
    
    return random.choice(intros)


def add_modern_comparisons(
    document_text: str,
    document_metadata: dict,
    document_type: str,
    groq_api_key: str = None,
    num_comparisons: int = 2
) -> str:
    """
    Add modern context/comparisons to boost "Educational Commentary" value
    These will be interspersed throughout the reading
    """
    
    import requests
    
    api_key = groq_api_key or GROQ_API_KEY
    
    # Get first 2000 chars to understand context
    sample = document_text[:2000]
    
    prompt = f"""Analyze this historical {document_type} excerpt and provide {num_comparisons} brief "modern comparison" notes.

Document excerpt:
{sample}

Year: {document_metadata.get('year', 'Unknown')}

For each comparison, write a 2-3 sentence note that:
1. References a specific part of the document
2. Connects it to modern technology, law, or practice
3. Is educational and interesting (not forced)

Format each as a natural narrator aside, like:
"Interestingly, this same principle would later influence..."
"What's remarkable here is that even today, we see..."

Return as a JSON array of strings. Example:
["Interestingly, this navigation method...", "What's remarkable is..."]

Return ONLY the JSON array, nothing else."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # Parse JSON array
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                comparisons = json.loads(match.group())
                return comparisons
        
        return []
            
    except Exception as e:
        print(f"  Comparison generation error: {e}")
        return []


def generate_outro(document_metadata: dict, duration_minutes: int) -> str:
    """Generate a brief outro for the video"""
    
    outros = [
        f"And so concludes our reading of {document_metadata.get('title', 'this document')}. These words, written over a century ago, remind us that the past is never truly gone. Until next time, sleep well.",
        
        f"We have reached the end of tonight's document. Thank you for joining me in the archives. May these old words bring you peaceful rest. Goodnight.",
        
        f"Thus ends our time with this {document_metadata.get('year', 'historical')} text. The archive holds many more secrets. But for now, rest. We shall return.",
        
        f"The document is complete. As you drift toward sleep, carry with you the knowledge that history is always waiting to be rediscovered. Pleasant dreams."
    ]
    
    return random.choice(outros)


def create_full_script(
    document_text: str,
    document_metadata: dict,
    document_type: str,
    target_minutes: int,
    groq_api_key: str = None
) -> dict:
    """
    Create a complete video script with intro, document, comparisons, and outro
    """
    
    from scripts.document_fetcher import split_text_for_duration
    
    print("  Generating curator introduction...")
    intro = generate_curator_intro(document_metadata, document_type, groq_api_key)
    
    print("  Generating modern comparisons...")
    comparisons = add_modern_comparisons(
        document_text, 
        document_metadata, 
        document_type, 
        groq_api_key
    )
    
    print("  Generating outro...")
    outro = generate_outro(document_metadata, target_minutes)
    
    # Split document for duration (account for intro/outro time)
    document_minutes = target_minutes - 2  # Reserve 2 min for intro/outro
    main_text = split_text_for_duration(document_text, document_minutes)
    
    # Insert comparisons at natural break points
    if comparisons:
        paragraphs = main_text.split('\n\n')
        if len(paragraphs) > len(comparisons) * 2:
            # Insert comparisons at intervals
            interval = len(paragraphs) // (len(comparisons) + 1)
            for i, comp in enumerate(comparisons):
                insert_pos = (i + 1) * interval
                if insert_pos < len(paragraphs):
                    paragraphs.insert(insert_pos, f"\n[Pause]\n{comp}\n[Pause]")
            main_text = '\n\n'.join(paragraphs)
    
    # Combine all parts
    full_script = f"{intro}\n\n[Pause - 3 seconds]\n\n{main_text}\n\n[Pause - 2 seconds]\n\n{outro}"
    
    return {
        "full_script": full_script,
        "intro": intro,
        "main_text": main_text,
        "comparisons": comparisons,
        "outro": outro,
        "word_count": len(full_script.split()),
        "estimated_minutes": round(len(full_script.split()) / 120)  # 120 wpm for slow
    }