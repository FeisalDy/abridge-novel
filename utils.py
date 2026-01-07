import os
import re
from typing import List, Callable, Optional
from dotenv import load_dotenv
load_dotenv()
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
    guardrail_callback: Optional[Callable[[str, str, str, str], None]] = None,
    intermediate_dir: Optional[str] = None,
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
    
    RESUME SUPPORT:
    When intermediate_dir is provided, each intermediate group result is saved
    to disk immediately after condensation. On subsequent runs, existing files
    are loaded instead of re-condensing, enabling resume after interruption.
    
    Args:
        units: List of text strings to condense (e.g., condensed arcs).
        condense_fn: Function that takes merged text and returns condensed text.
                     Must use the same BASE_CONDENSATION_PROMPT.
        max_tokens: Maximum estimated tokens allowed for input.
        units_per_group: Number of units to group in each intermediate layer.
        layer_name: Label for logging (e.g., "arc", "super-arc").
        verbose: Whether to print progress information.
        guardrail_callback: Optional callback for recording condensation metrics.
                           Signature: (input_text, output_text, stage, unit_id) -> None
        intermediate_dir: Optional directory to save intermediate layer outputs.
                         If provided, enables resume after interruption.
    
    Returns:
        The final condensed text that fits within the token limit.
    
    Design notes:
    - Grouping is purely positional/deterministic, not semantic.
    - The same condensation prompt is used at every layer.
    - Intermediate outputs are saved if intermediate_dir is provided.
    - This function is idempotent: small inputs pass through with one condensation.
    """
    if not units:
        raise ValueError("Cannot reduce empty list of units")
    
    # Merge all units
    merged_text = "\n\n".join(units)
    estimated_tokens = estimate_tokens(merged_text)
    
    if verbose:
        print(f"  [Hierarchy] Layer '{layer_name}': {len(units)} units, ~{estimated_tokens} tokens")
    
    # Base case: merged text fits within limit
    if estimated_tokens <= max_tokens:
        if verbose:
            print(f"  [Hierarchy] Layer '{layer_name}' fits within limit, condensing...")
        result = condense_fn(merged_text)
        
        # GUARDRAIL: Record compression ratio for final condensation.
        # This is observational only - does not modify output or block execution.
        if guardrail_callback is not None:
            guardrail_callback(merged_text, result, layer_name, f"{layer_name}_final")
        
        return result
    
    # Recursive case: input too large, need hierarchical reduction
    # Group units deterministically by fixed count
    # This is NOT semantic grouping - purely positional for reproducibility
    condensed_groups = []
    num_groups = (len(units) + units_per_group - 1) // units_per_group
    
    if verbose:
        print(f"  [Hierarchy] Layer '{layer_name}' exceeds {max_tokens} token limit")
        print(f"  [Hierarchy] Creating intermediate reduction ({num_groups} groups)")
    
    # Create intermediate layer directory if persistence is enabled
    layer_dir = None
    if intermediate_dir is not None:
        layer_dir = os.path.join(intermediate_dir, layer_name)
        os.makedirs(layer_dir, exist_ok=True)
    
    for i in range(0, len(units), units_per_group):
        group = units[i:i + units_per_group]
        group_index = i // units_per_group + 1
        
        # RESUME SUPPORT: Check if this group was already condensed in a previous run.
        # This enables resuming after interruption without re-doing completed work.
        group_filename = f"group_{group_index:03d}.condensed.txt"
        group_filepath = os.path.join(layer_dir, group_filename) if layer_dir else None
        
        if group_filepath and os.path.isfile(group_filepath):
            # Load existing condensed group from disk
            if verbose:
                print(f"  [Group] {group_index} / {num_groups} - Loading from disk (resume)")
            with open(group_filepath, "r", encoding="utf-8") as f:
                group_condensed = f.read()
        else:
            # Condense this group
            if verbose:
                print(f"  [Group] {group_index} / {num_groups} - Condensing ({len(group)} units)")
            
            group_merged = "\n\n".join(group)
            group_condensed = condense_fn(group_merged)
            
            # GUARDRAIL: Record compression ratio for intermediate group.
            # This is observational only - does not modify output or block execution.
            if guardrail_callback is not None:
                guardrail_callback(group_merged, group_condensed, layer_name, f"{layer_name}_group_{group_index:02d}")
            
            # PERSISTENCE: Save immediately after condensation to enable resume.
            # Each group is saved as soon as it completes, so interruption only
            # loses the currently-in-progress group, not all previous work.
            if group_filepath:
                with open(group_filepath, "w", encoding="utf-8") as f:
                    f.write(group_condensed)
                if verbose:
                    print(f"  [Group] {group_index} / {num_groups} - Saved to disk")
        
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
        guardrail_callback=guardrail_callback,
        intermediate_dir=intermediate_dir,
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

