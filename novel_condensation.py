import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm
from utils import reduce_until_fit
from guardrails import record_condensation
from cost_tracking import record_llm_usage

# --------------------------------------------------
# Configuration
# --------------------------------------------------

ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm()

# Maximum retries for LLM calls before failing
MAX_LLM_RETRIES = 3


def run_llm(prompt: str, stage: str = "novel", unit_id: str = "") -> str:
    """
    Run the LLM and track usage.
    
    Uses generate_with_usage() to capture token counts from the API response.
    Falls back to generate() if the LLM provider doesn't support usage tracking.
    
    Retries up to MAX_LLM_RETRIES times on failure.
    Raises RuntimeError if all retries fail - never returns None.
    """
    last_error = None
    
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            if hasattr(llm, 'generate_with_usage'):
                response = llm.generate_with_usage(prompt)
                
                # COST TRACKING: Record the LLM call with actual token counts.
                # This is observational only - does not modify output or block execution.
                if response.input_tokens is not None and response.output_tokens is not None:
                    record_llm_usage(
                        model=response.model,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        stage=stage,
                        unit_id=unit_id,
                    )
                
                if response.text is not None:
                    return response.text
                else:
                    raise RuntimeError("LLM returned empty response")
            else:
                # Fallback for LLM providers that don't support usage tracking
                result = llm.generate(prompt)
                if result is not None:
                    return result
                else:
                    raise RuntimeError("LLM returned empty response")
                    
        except Exception as e:
            last_error = e
            if attempt < MAX_LLM_RETRIES:
                print(f"  ⚠️ LLM error for {unit_id} (attempt {attempt}/{MAX_LLM_RETRIES}): {e}")
                print(f"  ↻ Retrying...")
            else:
                print(f"  🔴 LLM error for {unit_id} (attempt {attempt}/{MAX_LLM_RETRIES}): {e}")
    
    # All retries exhausted - raise error to stop pipeline
    raise RuntimeError(f"LLM failed after {MAX_LLM_RETRIES} attempts for {unit_id}: {last_error}")


# --------------------------------------------------
# Core logic
# --------------------------------------------------

def condense_text(text: str, stage: str = "novel", unit_id: str = "") -> str:
    """
    Apply the base condensation prompt to any text.
    
    This is the atomic condensation operation used at all hierarchy levels.
    The same prompt is applied whether condensing arcs, super-arcs, or
    the final novel.
    
    Args:
        text: The text to condense
        stage: Pipeline stage for cost tracking (e.g., "arc", "super-arc")
        unit_id: Identifier for cost tracking (e.g., "arc_group_01")
    
    Returns:
        The condensed text.
    
    Raises:
        RuntimeError: If LLM fails after all retries.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text
    )
    return run_llm(prompt, stage=stage, unit_id=unit_id)


def make_condense_fn_with_tracking(stage: str):
    """
    Create a condense function closure that tracks cost.
    
    This is used by reduce_until_fit() which calls condense_fn(text) without
    knowing about cost tracking. The closure captures the stage and generates
    appropriate unit_ids.
    
    Args:
        stage: Base stage name (e.g., "arc"). Will be updated by reduce_until_fit
               as it creates intermediate layers (e.g., "super-arc").
    
    Returns:
        A condense function compatible with reduce_until_fit's signature.
    """
    call_counter = [0]  # Mutable counter in closure
    
    def condense_fn(text: str) -> str:
        call_counter[0] += 1
        # Generate a unit_id based on call order
        # The actual stage/unit_id for guardrails is handled separately
        # This is just for cost tracking attribution
        unit_id = f"reduce_call_{call_counter[0]:03d}"
        return condense_text(text, stage=stage, unit_id=unit_id)
    
    return condense_fn


# Legacy alias for backward compatibility
condense_novel = condense_text


def process_novel(novel_name: str) -> None:
    """
    Produce the final condensed novel from arc-level outputs.
    
    SCALABILITY FIX:
    The original implementation assumed all condensed arcs could be merged
    and processed in a single LLM call. This fails for extremely large novels
    where the combined arc text exceeds the model's context window.
    
    The fix uses reduce_until_fit() which:
    1. Checks if the merged input fits within the token limit.
    2. If yes, performs a single condensation (original behavior preserved).
    3. If no, creates intermediate hierarchical layers by grouping arcs
       deterministically and condensing each group, then recursing.
    
    This maintains:
    - The same condensation prompt at all levels.
    - Deterministic, reproducible grouping (by position, not semantics).
    - Original behavior for small novels that already fit.
    """
    input_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(NOVEL_CONDENSED_DIR, novel_name)

    if not os.path.isdir(input_dir):
        raise ValueError(f"Arc directory not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    arc_files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".condensed.txt")
    )

    if not arc_files:
        raise ValueError("No arc files found")

    # PROGRESS: Report total count at stage start for visibility
    print(f"[Stage] Starting novel condensation ({len(arc_files)} arcs)")

    # Load all condensed arc texts as separate units
    arc_texts = []
    for filename in arc_files:
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            arc_texts.append(f.read())

    # GUARDRAIL: Create callback for recording condensation metrics.
    # This wrapper adapts record_condensation to the callback signature expected by reduce_until_fit.
    def guardrail_callback(input_text: str, output_text: str, stage: str, unit_id: str) -> None:
        record_condensation(
            input_text=input_text,
            output_text=output_text,
            stage=stage,
            unit_id=unit_id,
        )

    # RESUME SUPPORT: Use output_dir as intermediate storage for hierarchical layers.
    # This enables resume after interruption - intermediate groups are saved to disk
    # immediately after condensation and reloaded on subsequent runs.
    # Directory structure: output_dir/arc/group_001.condensed.txt, etc.
    intermediate_dir = output_dir

    # COST TRACKING: Create a condense function with tracking enabled.
    # This closure captures cost tracking context for each LLM call made by reduce_until_fit.
    condense_fn = make_condense_fn_with_tracking(stage="novel")

    # Use reduce_until_fit to handle arbitrary input sizes.
    # For small novels: behaves like original (single condensation pass).
    # For large novels: creates intermediate hierarchy layers as needed.
    condensed_novel = reduce_until_fit(
        units=arc_texts,
        condense_fn=condense_fn,
        layer_name="arc",
        verbose=True,
        guardrail_callback=guardrail_callback,
        intermediate_dir=intermediate_dir,
    )

    output_path = os.path.join(output_dir, "novel.condensed.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(condensed_novel)

    # PROGRESS: Stage completion log
    print(f"[Stage] Finished novel condensation")
    print(f"[Output] {output_path}")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python novel_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)
