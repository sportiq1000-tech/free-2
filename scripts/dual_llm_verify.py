"""
Dual-LLM Verification System for The Bureaucratic Archivist
Two AI models verify content quality through structured debate

LLM 1: GPT-OSS-120B (The Finder)
LLM 2: Llama-3.3-70B (The Verifier)
"""

import os
import requests
import re
import json
from typing import Dict, Optional, Tuple

# Configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Model configuration
MODELS = {
    "finder": "openai/gpt-oss-120b",      # Finds content
    "verifier": "llama-3.3-70b-versatile"  # Verifies finding
}


def call_llm(model: str, prompt: str, api_key: str = None, max_tokens: int = 200) -> Optional[str]:
    """
    Make API call to Groq with specified model
    """
    
    key = api_key or GROQ_API_KEY
    
    if not key:
        print(f"  ❌ No API key for {model}")
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
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"  ❌ API error {response.status_code}: {response.text[:100]}")
            return None
            
    except Exception as e:
        print(f"  ❌ API call failed: {str(e)[:50]}")
        return None


def llm1_find_content(text_sample: str, api_key: str = None) -> Dict:
    """
    LLM 1 (GPT-OSS-120B): Find where real content starts
    Returns: {"position": int, "reasoning": str, "snippet": str}
    """
    
    prompt = f"""You are an expert archival document processor.

Analyze this document beginning:

\"\"\"{text_sample}\"\"\"

Find where the ACTUAL HISTORICAL CONTENT begins.

SKIP these (they are NOT content):
- Project Gutenberg headers/license
- "Produced by", "Transcribed by" notes
- Title pages, publication info
- Table of contents
- Modern editor introductions
- Any text ABOUT the document

FIND the first line of the ORIGINAL DOCUMENT TEXT:
- Actual rules, regulations, procedures
- Historical narrative
- Official government language
- Chapter 1 / Section 1 / Article I

Respond in this EXACT JSON format:
{{
    "position": <character number where content starts>,
    "reasoning": "<why you chose this position>",
    "first_words": "<first 10 words of real content>"
}}

Return ONLY the JSON, nothing else."""

    result = call_llm(MODELS["finder"], prompt, api_key, max_tokens=300)
    
    if not result:
        return {"position": 0, "reasoning": "API failed", "first_words": ""}
    
    # Parse JSON from response
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "position": int(data.get("position", 0)),
                "reasoning": data.get("reasoning", ""),
                "first_words": data.get("first_words", "")
            }
    except:
        pass
    
    # Try to extract just number
    number_match = re.search(r'\d+', result)
    if number_match:
        return {
            "position": int(number_match.group()),
            "reasoning": result,
            "first_words": ""
        }
    
    return {"position": 0, "reasoning": "Failed to parse", "first_words": ""}


def llm2_verify_content(
    text_sample: str, 
    llm1_position: int, 
    llm1_reasoning: str,
    llm1_first_words: str,
    api_key: str = None
) -> Dict:
    """
    LLM 2 (Llama-3.3-70B): Verify LLM 1's finding
    Returns: {"agrees": bool, "reasoning": str, "suggested_position": int}
    """
    
    # Get snippet from LLM 1's position
    snippet_start = max(0, llm1_position - 50)
    snippet_end = min(len(text_sample), llm1_position + 500)
    snippet = text_sample[snippet_start:snippet_end]
    
    prompt = f"""You are a verification expert checking another AI's work.

ORIGINAL DOCUMENT START:
\"\"\"{text_sample[:2000]}\"\"\"

FIRST AI (GPT-OSS-120B) SAID:
- Content starts at character: {llm1_position}
- Reasoning: {llm1_reasoning}
- First words: {llm1_first_words}

TEXT AT THAT POSITION:
\"\"\"{snippet}\"\"\"

YOUR JOB: Verify if this is ACTUALLY where historical content begins.

Check for these PROBLEMS:
1. Is this still metadata/header? (Project Gutenberg info, "Produced by", etc.)
2. Is this a table of contents? (Chapter names with page numbers)
3. Is this a modern introduction? (Written ABOUT the document)
4. Is this the actual historical text? (The original document)

Respond in this EXACT JSON format:
{{
    "agrees": <true or false>,
    "reasoning": "<why you agree or disagree>",
    "suggested_position": <better position if you disagree, or same position if you agree>,
    "confidence": "<high, medium, or low>"
}}

Return ONLY the JSON, nothing else."""

    result = call_llm(MODELS["verifier"], prompt, api_key, max_tokens=300)
    
    if not result:
        return {"agrees": True, "reasoning": "API failed, defaulting to agree", "suggested_position": llm1_position, "confidence": "low"}
    
    # Parse JSON
    try:
        json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "agrees": data.get("agrees", True),
                "reasoning": data.get("reasoning", ""),
                "suggested_position": int(data.get("suggested_position", llm1_position)),
                "confidence": data.get("confidence", "medium")
            }
    except:
        pass
    
    # Default to agree if can't parse
    return {"agrees": True, "reasoning": result, "suggested_position": llm1_position, "confidence": "low"}


def llm_debate_round(
    text_sample: str,
    llm1_position: int,
    llm2_criticism: str,
    round_num: int,
    api_key: str = None
) -> Dict:
    """
    LLM 1 responds to LLM 2's criticism and finds new position
    """
    
    prompt = f"""You are an expert archival document processor.

DOCUMENT:
\"\"\"{text_sample}\"\"\"

YOUR PREVIOUS FINDING:
- Position: {llm1_position}

VERIFIER'S CRITICISM:
{llm2_criticism}

The verifier disagreed with your position. They may be right.

Look again at the document and find a BETTER starting position.
Consider their feedback carefully.

SKIP:
- Any metadata or headers
- Table of contents
- Modern introductions

FIND:
- The ACTUAL original historical text
- Where the real document begins

Respond in this EXACT JSON format:
{{
    "new_position": <new character number>,
    "reasoning": "<why this is better>",
    "first_words": "<first 10 words at new position>"
}}

Return ONLY the JSON."""

    result = call_llm(MODELS["finder"], prompt, api_key, max_tokens=300)
    
    if not result:
        return {"new_position": llm1_position, "reasoning": "API failed", "first_words": ""}
    
    try:
        json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {
                "new_position": int(data.get("new_position", llm1_position)),
                "reasoning": data.get("reasoning", ""),
                "first_words": data.get("first_words", "")
            }
    except:
        pass
    
    return {"new_position": llm1_position, "reasoning": "Failed to parse", "first_words": ""}


def dual_llm_find_content(raw_text: str, api_key: str = None, max_rounds: int = 3) -> Dict:
    """
    Main function: Two LLMs debate to find content start
    
    Returns:
    {
        "position": int,
        "confidence": str,
        "rounds": int,
        "final_reasoning": str,
        "agreed": bool
    }
    """
    
    print("  🤖 Starting Dual-LLM Verification...")
    
    # Take sample for analysis
    sample = raw_text[:min(15000, len(raw_text))]
    
    # Round 1: LLM 1 finds position
    print(f"  📍 LLM 1 ({MODELS['finder'][:20]}...) finding content...")
    llm1_result = llm1_find_content(sample, api_key)
    position = llm1_result["position"]
    
    print(f"     → Position: {position:,}")
    print(f"     → Reasoning: {llm1_result['reasoning'][:60]}...")
    
    # Round 1: LLM 2 verifies
    print(f"  🔍 LLM 2 ({MODELS['verifier'][:20]}...) verifying...")
    llm2_result = llm2_verify_content(
        sample,
        position,
        llm1_result["reasoning"],
        llm1_result["first_words"],
        api_key
    )
    
    if llm2_result["agrees"]:
        print(f"     → ✅ AGREES! Confidence: {llm2_result['confidence']}")
        return {
            "position": position,
            "confidence": llm2_result["confidence"],
            "rounds": 1,
            "final_reasoning": llm2_result["reasoning"],
            "agreed": True
        }
    
    print(f"     → ❌ DISAGREES: {llm2_result['reasoning'][:60]}...")
    
    # Debate rounds
    for round_num in range(2, max_rounds + 1):
        print(f"  💬 Debate Round {round_num}...")
        
        # LLM 1 tries again with LLM 2's feedback
        print(f"     LLM 1 reconsidering...")
        debate_result = llm_debate_round(
            sample,
            position,
            llm2_result["reasoning"],
            round_num,
            api_key
        )
        
        new_position = debate_result["new_position"]
        print(f"     → New position: {new_position:,}")
        
        # LLM 2 verifies again
        print(f"     LLM 2 verifying...")
        llm2_result = llm2_verify_content(
            sample,
            new_position,
            debate_result["reasoning"],
            debate_result["first_words"],
            api_key
        )
        
        if llm2_result["agrees"]:
            print(f"     → ✅ AGREES! Confidence: {llm2_result['confidence']}")
            return {
                "position": new_position,
                "confidence": llm2_result["confidence"],
                "rounds": round_num,
                "final_reasoning": llm2_result["reasoning"],
                "agreed": True
            }
        
        print(f"     → ❌ Still disagrees...")
        position = new_position
    
    # Max rounds reached - use LLM 2's suggested position
    final_position = llm2_result.get("suggested_position", position)
    print(f"  ⚠️ Max rounds reached. Using position: {final_position:,}")
    
    return {
        "position": final_position,
        "confidence": "low",
        "rounds": max_rounds,
        "final_reasoning": "Max debate rounds reached",
        "agreed": False
    }


def verify_historical_content(text: str, claimed_year: int = None, api_key: str = None) -> Dict:
    """
    Final verification: Is this ACTUALLY historical content?
    Uses both LLMs to cross-check
    """
    
    sample = text[:2000]
    
    prompt = f"""Analyze this text for historical authenticity:

\"\"\"{sample}\"\"\"

Claimed document year: {claimed_year or 'Unknown'}

CHECK FOR:
1. Modern language ("pre-war", "internet", "computer")
2. Anachronistic references
3. Modern editorial comments
4. Project Gutenberg boilerplate
5. "Produced by" or "Transcribed by" notes

Is this GENUINE historical content from the claimed era?

Respond in JSON:
{{
    "is_historical": <true or false>,
    "modern_phrases_found": ["list", "of", "phrases"],
    "confidence": "<high, medium, low>",
    "reasoning": "<explanation>"
}}"""

    # Ask both LLMs
    result1 = call_llm(MODELS["finder"], prompt, api_key, max_tokens=300)
    result2 = call_llm(MODELS["verifier"], prompt, api_key, max_tokens=300)
    
    # Parse results
    def parse_result(result):
        if not result:
            return {"is_historical": True, "confidence": "low"}
        try:
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"is_historical": True, "confidence": "low"}
    
    parsed1 = parse_result(result1)
    parsed2 = parse_result(result2)
    
    # Both must agree it's historical
    both_agree = parsed1.get("is_historical", True) and parsed2.get("is_historical", True)
    
    return {
        "is_historical": both_agree,
        "llm1_says": parsed1.get("is_historical", True),
        "llm2_says": parsed2.get("is_historical", True),
        "confidence": "high" if both_agree else "low",
        "reasoning": parsed1.get("reasoning", "") + " | " + parsed2.get("reasoning", "")
    }


# Test function
if __name__ == "__main__":
    test_text = """
    The Project Gutenberg eBook of Robert's Rules of Order
    
    Produced by John Smith
    
    *** START OF THE PROJECT GUTENBERG EBOOK ***
    
    ROBERT'S RULES OF ORDER
    
    POCKET MANUAL OF RULES OF ORDER
    FOR DELIBERATIVE ASSEMBLIES
    
    BY HENRY M. ROBERT
    
    PART I.
    
    RULES OF ORDER.
    
    ART. I. INTRODUCTION OF BUSINESS.
    
    1. All business should be brought before the assembly
    by a motion of a member, or by the presentation of a
    communication to the assembly...
    """
    
    print("Testing Dual-LLM Verification...\n")
    result = dual_llm_find_content(test_text)
    print(f"\nFinal Result: {result}")