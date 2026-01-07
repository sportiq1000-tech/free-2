"""
Script Enhancer for The Bureaucratic Archivist
Transforms documents into "Senior Archivist" persona readings
with atmospheric, bureaucratic tone
"""

import os
import json
import random

# Get API key from environment
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')


def generate_archivist_intro(
    document_metadata: dict,
    document_type: str,
    groq_api_key: str = None
) -> str:
    """
    Generate a "Senior Archivist" persona introduction
    Creates atmospheric, bureaucratic tone
    """
    
    import requests
    
    api_key = groq_api_key or GROQ_API_KEY
    
    # Archivist persona styles
    personas = [
        {
            "name": "The Weary Cataloger",
            "style": "tired but precise, speaks slowly, finds comfort in procedure",
            "tone": "methodical and slightly detached"
        },
        {
            "name": "The Basement Archivist", 
            "style": "has been in this office for decades, quiet authority, no rush",
            "tone": "calm, professional, faintly melancholic"
        },
        {
            "name": "The Night Shift Curator",
            "style": "works alone in the archives after hours, intimate and careful",
            "tone": "soft, contemplative, reassuring"
        }
    ]
    
    persona = random.choice(personas)
    
    # Use document ID or create archive reference
    archive_ref = f"{random.randint(100, 999)}-{chr(random.randint(65, 90))}"
    
    prompt = f"""You are "{persona['name']}" - a {persona['style']} senior archivist working in a government archive.

Write a 60-90 second introduction (150-200 words) for a late-night archival reading of this document:

Document Title: {document_metadata.get('title', 'Unknown')[:100]}
Document Type: {document_type.replace('_', ' ').title()}
Year: {document_metadata.get('year', 'Unknown')}
Archive Reference: Document {archive_ref}

Your introduction must:
1. Welcome the listener with quiet professionalism (vary greetings - not always "welcome")
2. State the archive reference number for authenticity
3. Briefly explain what this document IS (be specific about the bureaucracy)
4. Mention why it has been preserved (historical/administrative value)
5. Set a calm, meditative tone - make it clear there is no rush
6. End with a gentle transition: "We begin." or "Let us proceed." or similar

Tone: {persona['tone']}

Important: 
- Use phrases like "Box [number]," "Folder [letter]," "Section [number]"
- Mention the weight or texture of the document if appropriate
- Do NOT be cheerful or excited
- Sound like someone who has done this for forty years
- Create a "space" for the listener (the archive room)

Write ONLY the spoken introduction. No stage directions, no [brackets], just the words to be read.

Begin:"""

    if api_key:
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
                        {
                            "role": "system", 
                            "content": "You are a thoughtful senior archivist who creates calm, atmospheric introductions to historical documents."
                        },
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
                return generate_fallback_archivist_intro(document_metadata, document_type, archive_ref)
                
        except Exception as e:
            print(f"  Intro generation error: {e}")
            return generate_fallback_archivist_intro(document_metadata, document_type, archive_ref)
    else:
        return generate_fallback_archivist_intro(document_metadata, document_type, archive_ref)


def generate_fallback_archivist_intro(metadata: dict, doc_type: str, archive_ref: str = None) -> str:
    """Generate atmospheric intro without API (fallback)"""
    
    if not archive_ref:
        archive_ref = f"{random.randint(100, 999)}-{chr(random.randint(65, 90))}"
    
    year = metadata.get('year', 'unknown year')
    title = metadata.get('title', 'this document')
    doc_category = doc_type.replace('_', ' ')
    
    intros = [
        f"Welcome to the Central Archive. You are here for processing. "
        f"I am your Senior Archivist. Tonight we are reviewing Document {archive_ref}, "
        f"housed in the {doc_category} collection. The document before us: {title}, "
        f"dated {year}. This record has been preserved for administrative reference. "
        f"Please... make yourself comfortable. The reading is lengthy. There is no need to remain alert. "
        f"We begin.",
        
        f"Good evening. Or perhaps it is already morning. Time moves differently here in the archives. "
        f"I have retrieved Document {archive_ref} from the {doc_category} section. "
        f"The file reads: {title}, year {year}. Heavy paper. Faded ink. But the words... "
        f"the words remain. Let us proceed with the intake.",
        
        f"You may sit. The chair by the filing cabinet is available. "
        f"I am conducting a review of Archive Box {archive_ref}, "
        f"which contains {title} from our {doc_category} collection, circa {year}. "
        f"Standard procedure requires a complete reading. You are welcome to observe. "
        f"Or rest. Many do. The fluorescent lights have a calming frequency. We begin the review now.",
        
        f"Another evening in the basement. Another document to catalog. "
        f"This one is Reference {archive_ref}: {title}. Filed under {doc_category}. "
        f"The year is marked as {year}. Remarkable, in a sense, that such records endure. "
        f"Unremarkable in their content, perhaps. But procedure demands their preservation. "
        f"Shall we? Let us read."
    ]
    
    return random.choice(intros)


def generate_archivist_outro(document_metadata: dict, duration_minutes: int) -> str:
    """Generate atmospheric outro"""
    
    outros = [
        "The document is complete. The file will be returned to its proper location. "
        "You may remain as long as you wish. The archive is always... patient. "
        "Until we meet again.",
        
        "And so we conclude tonight's reading. The ledger is closed. The lights remain on. "
        "They always do. Rest now. The archives will be here when you wake.",
        
        "This completes the intake for this session. You have been... adequately still. "
        "The basement is quiet again. As it should be. Sleep well. We shall return.",
        
        "Processing complete. The record has been reviewed and will be re-filed. "
        "Thank you for your patience. Or your silence. Both are appreciated here. Goodnight."
    ]
    
    return random.choice(outros)


def add_modern_comparisons(
    document_text: str,
    document_metadata: dict,
    document_type: str,
    groq_api_key: str = None,
    num_comparisons: int = 2
) -> list:
    """
    Add subtle modern context notes (educational value)
    Less "exciting," more bureaucratic observation
    """
    
    import requests
    
    api_key = groq_api_key or GROQ_API_KEY
    
    sample = document_text[:2000]
    
    prompt = f"""You are a tired but knowledgeable archivist reviewing this historical {document_type} excerpt:

{sample}

Year: {document_metadata.get('year', 'Unknown')}

Provide {num_comparisons} brief observations connecting this to modern administrative practices or regulations.

Tone: Dry, bureaucratic, observational. NOT enthusiastic.

Format each as a single, matter-of-fact statement (2-3 sentences max):
- "Of note: this procedure would later influence..."
- "The terminology here persists in modern..."
- "Interestingly, the categorization system..."

Return ONLY a JSON array of strings. No other text.

Example: ["Of note: this filing system...", "The terminology here..."]
"""

    if api_key:
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 400
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                import re
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    comparisons = json.loads(match.group())
                    return comparisons
            
            return []
                
        except Exception as e:
            print(f"  Comparison generation error: {e}")
            return []
    
    return []


def create_full_script(
    document_text: str,
    document_metadata: dict,
    document_type: str,
    target_minutes: int,
    groq_api_key: str = None
) -> dict:
    """
    Create complete video script with Archivist persona
    """
    
    print("  Generating archivist introduction...")
    intro = generate_archivist_intro(document_metadata, document_type, groq_api_key)
    
    print("  Generating modern comparisons...")
    comparisons = add_modern_comparisons(
        document_text, 
        document_metadata, 
        document_type, 
        groq_api_key
    )
    
    print("  Generating outro...")
    outro = generate_archivist_outro(document_metadata, target_minutes)
    
    # Import splitting function
    from document_scraper import split_text_for_duration
    
    # Split document for duration (account for intro/outro)
    document_minutes = target_minutes - 2
    main_text = split_text_for_duration(document_text, document_minutes, words_per_minute=120)
    
    # Insert comparisons at natural break points (if any)
    if comparisons:
        paragraphs = main_text.split('\n\n')
        if len(paragraphs) > len(comparisons) * 2:
            interval = len(paragraphs) // (len(comparisons) + 1)
            for i, comp in enumerate(comparisons):
                insert_pos = (i + 1) * interval
                if insert_pos < len(paragraphs):
                    paragraphs.insert(insert_pos, f"\n[Pause]\n{comp}\n[Pause]")
            main_text = '\n\n'.join(paragraphs)
    
    # Combine with longer pauses for bureaucratic effect
    full_script = f"{intro}\n\n[Pause - 3 seconds]\n\n{main_text}\n\n[Pause - 3 seconds]\n\n{outro}"
    
    return {
        "full_script": full_script,
        "intro": intro,
        "main_text": main_text,
        "comparisons": comparisons,
        "outro": outro,
        "word_count": len(full_script.split()),
        "estimated_minutes": round(len(full_script.split()) / 120)
    }