import os
import re
from typing import List, Callable

# --------------------------------------------------
# Token estimation and context limit configuration
# --------------------------------------------------

# Conservative token limit for input text.
# This accounts for the condensation prompt overhead and leaves room for output.
# Assumption: Most LLMs have 128k+ context, but we target a safe input limit.
# This can be overridden via environment variable if needed.
DEFAULT_SAFE_TOKEN_LIMIT = int(os.getenv("CONDENSATION_TOKEN_LIMIT", "60000"))

# Default number of units to group when hierarchical reduction is needed.
# This controls how many condensed units are merged in each intermediate layer.
DEFAULT_UNITS_PER_GROUP = 10


def estimate_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string using the appropriate tokenizer
    for the current LLM provider.
    
    Uses the actual model tokenizer where available:
    - gemini: Google's genai count_tokens API
    - copilot, deepseek, groq, cerebras: tiktoken (OpenAI-compatible)
    - vllm: HuggingFace tokenizer if available, else tiktoken
    - ollama: tiktoken fallback
    
    Returns:
        The number of tokens in the text.
    """
    from llm.tokenizer import count_tokens
    return count_tokens(text)


def reduce_until_fit(
    units: List[str],
    condense_fn: Callable[[str], str],
    max_tokens: int = DEFAULT_SAFE_TOKEN_LIMIT,
    units_per_group: int = DEFAULT_UNITS_PER_GROUP,
    layer_name: str = "unit",
    verbose: bool = True,
) -> str:
    """
    Recursively condense a list of text units until the merged result fits
    within the token limit.
    
    This function solves the scalability problem where the final condensation
    step cannot fit all inputs into a single LLM context window.
    
    Algorithm:
    1. Merge all units into a single text.
    2. If the merged text fits within max_tokens, condense it once and return.
    3. If it doesn't fit, group units deterministically by fixed count,
       condense each group, and recurse with the condensed groups as new units.
    
    This creates an arbitrarily deep hierarchy of condensation layers,
    applied only when needed, without changing the condensation prompt or
    editorial behavior.
    
    Args:
        units: List of text strings to condense (e.g., condensed arcs).
        condense_fn: Function that takes merged text and returns condensed text.
                     Must use the same BASE_CONDENSATION_PROMPT.
        max_tokens: Maximum estimated tokens allowed for input.
        units_per_group: Number of units to group in each intermediate layer.
        layer_name: Label for logging (e.g., "arc", "super-arc").
        verbose: Whether to print progress information.
    
    Returns:
        The final condensed text that fits within the token limit.
    
    Design notes:
    - Grouping is purely positional/deterministic, not semantic.
    - The same condensation prompt is used at every layer.
    - Intermediate outputs could be saved if needed for inspection.
    - This function is idempotent: small inputs pass through with one condensation.
    """
    if not units:
        raise ValueError("Cannot reduce empty list of units")
    
    # Merge all units
    merged_text = "\n\n".join(units)
    estimated_tokens = estimate_tokens(merged_text)
    
    if verbose:
        print(f"  [{layer_name}] {len(units)} units, ~{estimated_tokens} tokens estimated")
    
    # Base case: merged text fits within limit
    if estimated_tokens <= max_tokens:
        if verbose:
            print(f"  [{layer_name}] Input fits within limit, condensing...")
        return condense_fn(merged_text)
    
    # Recursive case: input too large, need hierarchical reduction
    if verbose:
        print(f"  [{layer_name}] Input exceeds {max_tokens} token limit, "
              f"creating intermediate layer...")
    
    # Group units deterministically by fixed count
    # This is NOT semantic grouping - purely positional for reproducibility
    condensed_groups = []
    num_groups = (len(units) + units_per_group - 1) // units_per_group
    
    for i in range(0, len(units), units_per_group):
        group = units[i:i + units_per_group]
        group_index = i // units_per_group + 1
        
        if verbose:
            print(f"  [{layer_name}] Condensing intermediate group "
                  f"{group_index}/{num_groups} ({len(group)} units)...")
        
        group_merged = "\n\n".join(group)
        group_condensed = condense_fn(group_merged)
        condensed_groups.append(group_condensed)
    
    # Recurse with condensed groups as the new units
    # Increment layer name for clarity in logs
    next_layer_name = f"super-{layer_name}"
    
    return reduce_until_fit(
        units=condensed_groups,
        condense_fn=condense_fn,
        max_tokens=max_tokens,
        units_per_group=units_per_group,
        layer_name=next_layer_name,
        verbose=verbose,
    )


# --------------------------------------------------
# Text extraction utilities
# --------------------------------------------------

def extract_answer(text: str) -> str:
    # 1. Remove <think>...</think> completely
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # 2. Extract <answer> if present
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. Otherwise return remaining text
    return text.strip()

