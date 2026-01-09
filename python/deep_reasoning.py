"""
VERITAS - Deep Reasoning Analysis
Uses GPT-OSS 120B with reasoning for complex verification tasks
"""

from groq import Groq

# Initialize client
client = Groq()


def deep_analyze(content: str, reasoning_effort: str = "medium", stream: bool = True) -> str:
    """
    Perform deep analysis with enhanced reasoning capabilities.
    
    Args:
        content: The text/description to analyze
        reasoning_effort: "low", "medium", or "high" - controls depth of reasoning
        stream: Whether to stream the response
    
    Returns:
        Detailed forensic analysis with reasoning chain
    """
    system_prompt = """You are Veritas, an advanced forensic AI with deep reasoning capabilities.
    
Perform thorough analysis considering:
1. Surface-level patterns and indicators
2. Hidden implications and context
3. Cross-referencing with known facts
4. Chain of reasoning for each conclusion
5. Confidence calibration

Provide detailed reasoning for each finding.

Respond with JSON:
{
    "verdict": "Authentic" | "Fake/Generated" | "Inconclusive" | "Suspicious",
    "confidence": 0-100,
    "summary": "...",
    "reasoning_chain": [
        {"step": 1, "observation": "...", "implication": "...", "confidence": 0-100},
        ...
    ],
    "technicalDetails": [{"label": "...", "value": "...", "status": "pass|fail|warn", "explanation": "..."}],
    "final_reasoning": "..."
}"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Perform deep forensic analysis:\n\n{content}"}
        ],
        temperature=1,
        max_completion_tokens=8192,
        top_p=1,
        reasoning_effort=reasoning_effort,
        stream=stream,
        stop=None
    )

    if stream:
        result = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="")
            result += content
        print()
        return result
    else:
        return completion.choices[0].message.content


def compare_claims(claim1: str, claim2: str, reasoning_effort: str = "high") -> str:
    """
    Compare two claims and determine which is more credible.
    Uses high reasoning effort for thorough comparison.
    """
    prompt = f"""Compare these two claims and determine which is more credible:

CLAIM 1: {claim1}

CLAIM 2: {claim2}

Analyze each claim thoroughly, identify contradictions, and provide reasoned verdict."""

    return deep_analyze(prompt, reasoning_effort=reasoning_effort)


# Example usage
if __name__ == "__main__":
    # Test deep reasoning
    sample_content = """
    A viral social media post claims that a new vaccine has been secretly 
    developed using alien technology recovered from a crashed UFO in 1947.
    The post includes a blurry image of what appears to be a document with 
    government letterhead.
    """
    
    print("=== Deep Reasoning Analysis ===\n")
    print("Reasoning effort: high\n")
    result = deep_analyze(sample_content, reasoning_effort="high")
