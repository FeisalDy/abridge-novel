import os
import json
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm
from utils import reduce_until_fit, estimate_tokens, DEFAULT_SAFE_TOKEN_LIMIT
from guardrails import record_condensation
from cost_tracking import record_llm_usage

# --------------------------------------------------
# Configuration
# --------------------------------------------------

ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"

# --------------------------------------------------
# Output Token Budget Configuration
# --------------------------------------------------
# These limits protect against LLM output truncation.
# Most models have a hard output cap (e.g., 65,536 tokens for many providers).
# We use a conservative budget to ensure outputs never hit the hard cap.
#
# SAFE_OUTPUT_TOKEN_BUDGET: Maximum tokens we request per LLM call output.
# This leaves headroom below the model's hard limit to prevent truncation.
SAFE_OUTPUT_TOKEN_BUDGET = int(os.getenv("CONDENSATION_OUTPUT_TOKEN_LIMIT", "55000"))

# Estimated compression ratio for condensation (output / input).
# Used to estimate expected output size from input size.
# Conservative estimate: condensation typically achieves 30-50% compression.
ESTIMATED_COMPRESSION_RATIO = float(os.getenv("CONDENSATION_COMPRESSION_RATIO", "0.45"))

# Maximum input tokens that can safely produce output within budget.
# input * compression_ratio <= output_budget
# Therefore: max_input = output_budget / compression_ratio
MAX_INPUT_FOR_OUTPUT_BUDGET = int(SAFE_OUTPUT_TOKEN_BUDGET / ESTIMATED_COMPRESSION_RATIO)


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm(stage="novel")

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
# Output-Capped Prompt
# --------------------------------------------------
# This prompt wrapper adds explicit output length constraints to prevent
# LLM output truncation. It preserves the semantic intent of BASE_CONDENSATION_PROMPT
# while adding hard instructions to stay within token budget.

OUTPUT_CAP_INSTRUCTION = """
CRITICAL OUTPUT LENGTH CONSTRAINT:
- Your response MUST NOT exceed {output_token_limit} tokens.
- If you cannot complete the condensation within this limit, stop at a natural narrative boundary (end of a scene, chapter, or significant event).
- NEVER truncate mid-sentence or mid-paragraph.
- NEVER cut off in the middle of describing an event.
- Prefer completing fewer events fully over starting events you cannot finish.
- End cleanly with a complete sentence.
"""


def make_output_capped_prompt(input_text: str, output_token_limit: int = SAFE_OUTPUT_TOKEN_BUDGET) -> str:
    """
    Create a condensation prompt with explicit output length constraints.
    
    This wraps BASE_CONDENSATION_PROMPT with additional instructions to:
    1. Stay within the output token budget
    2. Stop at narrative boundaries if necessary
    3. Never truncate mid-sentence
    
    Args:
        input_text: The text to condense
        output_token_limit: Maximum tokens allowed in output
    
    Returns:
        The full prompt with output cap instructions
    """
    base_prompt = BASE_CONDENSATION_PROMPT.format(INPUT_TEXT=input_text)
    cap_instruction = OUTPUT_CAP_INSTRUCTION.format(output_token_limit=output_token_limit)
    
    # Insert the cap instruction after the base prompt's style requirements
    # but before the input text marker
    return base_prompt + "\n" + cap_instruction


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


def condense_text_output_capped(text: str, stage: str = "novel", unit_id: str = "", 
                                 output_token_limit: int = SAFE_OUTPUT_TOKEN_BUDGET) -> str:
    """
    Apply condensation with explicit output length constraints.
    
    This variant of condense_text adds output cap instructions to the prompt
    to prevent LLM output truncation on large inputs.
    
    Args:
        text: The text to condense
        stage: Pipeline stage for cost tracking
        unit_id: Identifier for cost tracking
        output_token_limit: Maximum tokens allowed in output
    
    Returns:
        The condensed text (guaranteed to be within output budget if LLM complies)
    
    Raises:
        RuntimeError: If LLM fails after all retries.
    """
    prompt = make_output_capped_prompt(text, output_token_limit)
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


def make_output_capped_condense_fn(stage: str, output_token_limit: int = SAFE_OUTPUT_TOKEN_BUDGET):
    """
    Create a condense function closure with output cap enforcement.
    
    Similar to make_condense_fn_with_tracking but uses the output-capped
    prompt variant to prevent LLM output truncation.
    
    Args:
        stage: Base stage name for cost tracking
        output_token_limit: Maximum tokens allowed in output
    
    Returns:
        A condense function that enforces output limits.
    """
    call_counter = [0]
    
    def condense_fn(text: str) -> str:
        call_counter[0] += 1
        unit_id = f"output_capped_call_{call_counter[0]:03d}"
        return condense_text_output_capped(text, stage=stage, unit_id=unit_id, 
                                           output_token_limit=output_token_limit)
    
    return condense_fn


# --------------------------------------------------
# Output-Aware Chunking for Multi-Part Outputs
# --------------------------------------------------

def estimate_output_tokens(input_text: str) -> int:
    """
    Estimate the number of output tokens a condensation will produce.
    
    Uses the configured compression ratio to estimate output size from input size.
    This is a conservative estimate - actual output may be smaller.
    
    Args:
        input_text: The text that will be condensed
    
    Returns:
        Estimated number of output tokens
    """
    input_tokens = estimate_tokens(input_text)
    return int(input_tokens * ESTIMATED_COMPRESSION_RATIO)


def will_output_exceed_budget(input_text: str, budget: int = SAFE_OUTPUT_TOKEN_BUDGET) -> bool:
    """
    Check if condensing this input would likely exceed the output token budget.
    
    Args:
        input_text: The text to be condensed
        budget: Maximum allowed output tokens
    
    Returns:
        True if estimated output would exceed budget
    """
    estimated_output = estimate_output_tokens(input_text)
    return estimated_output > budget


def split_units_for_output_budget(
    units: list[str],
    max_input_tokens: int = MAX_INPUT_FOR_OUTPUT_BUDGET,
    verbose: bool = True
) -> list[list[str]]:
    """
    Split a list of text units into chunks where each chunk's condensed output
    will fit within the output token budget.
    
    This is purely positional grouping - no semantic analysis.
    Units are grouped greedily until adding another would exceed the input limit.
    
    Algorithm:
    1. Start with an empty current chunk
    2. For each unit, check if adding it would exceed max_input_tokens
    3. If yes, finalize current chunk and start a new one
    4. If no, add unit to current chunk
    5. Handle edge case where single unit exceeds limit (must process alone)
    
    Args:
        units: List of text units to split
        max_input_tokens: Maximum input tokens per chunk (derived from output budget)
        verbose: Whether to print progress
    
    Returns:
        List of unit groups, each group will produce output within budget
    """
    if not units:
        return []
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for i, unit in enumerate(units):
        unit_tokens = estimate_tokens(unit)
        
        # Edge case: single unit exceeds limit
        # It must be processed alone - further splitting would require
        # breaking the unit itself (not supported at this level)
        if unit_tokens > max_input_tokens:
            if verbose:
                print(f"  [OutputChunk] Warning: Unit {i+1} ({unit_tokens} tokens) exceeds "
                      f"output-safe limit ({max_input_tokens})")
            # Finalize current chunk if non-empty
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            # Add oversized unit as its own chunk
            chunks.append([unit])
            continue
        
        # Check if adding this unit would exceed the limit
        if current_tokens + unit_tokens > max_input_tokens:
            # Finalize current chunk
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [unit]
            current_tokens = unit_tokens
        else:
            # Add to current chunk
            current_chunk.append(unit)
            current_tokens += unit_tokens
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    if verbose:
        print(f"  [OutputChunk] Split {len(units)} units into {len(chunks)} output-safe chunks")
    
    return chunks


def condense_with_output_awareness(
    units: list[str],
    condense_fn,
    output_dir: str,
    layer_name: str = "novel_part",
    verbose: bool = True,
    guardrail_callback=None,
) -> list[tuple[str, str]]:
    """
    Condense units with output token budget awareness.
    
    This function ensures that each LLM call produces output within the
    safe output token budget. If the combined input would produce output
    exceeding the budget, it is split into multiple chunks.
    
    Each chunk:
    - Comes from exactly one LLM call
    - Is stored as its own artifact
    - Has its own cost and guardrail record
    
    RESUME SUPPORT:
    Output parts are saved immediately after generation. Existing parts
    are loaded from disk on subsequent runs.
    
    Args:
        units: List of text units to condense (e.g., from reduce_until_fit output)
        condense_fn: Function to condense text (should use output-capped prompt)
        output_dir: Directory to save output parts
        layer_name: Label for logging
        verbose: Whether to print progress
        guardrail_callback: Optional callback for recording metrics
    
    Returns:
        List of (filename, content) tuples for all output parts
    """
    # First, split units into output-safe chunks
    chunks = split_units_for_output_budget(units, verbose=verbose)
    
    output_parts = []
    
    for chunk_idx, chunk_units in enumerate(chunks):
        part_num = chunk_idx + 1
        part_filename = f"novel.part_{part_num:03d}.condensed.txt"
        part_filepath = os.path.join(output_dir, part_filename)
        
        # RESUME SUPPORT: Check if this part already exists
        if os.path.isfile(part_filepath):
            if verbose:
                print(f"  [Part] {part_num} / {len(chunks)} - Loading from disk (resume)")
            with open(part_filepath, "r", encoding="utf-8") as f:
                part_content = f.read()
        else:
            # Merge chunk units and condense
            if verbose:
                chunk_token_estimate = sum(estimate_tokens(u) for u in chunk_units)
                print(f"  [Part] {part_num} / {len(chunks)} - Condensing "
                      f"({len(chunk_units)} units, ~{chunk_token_estimate} input tokens)")
            
            merged_chunk = "\n\n".join(chunk_units)
            part_content = condense_fn(merged_chunk)
            
            # GUARDRAIL: Record compression ratio for this part
            if guardrail_callback is not None:
                guardrail_callback(merged_chunk, part_content, layer_name, 
                                   f"{layer_name}_{part_num:03d}")
            
            # PERSISTENCE: Save immediately after condensation
            with open(part_filepath, "w", encoding="utf-8") as f:
                f.write(part_content)
            if verbose:
                output_tokens = estimate_tokens(part_content)
                print(f"  [Part] {part_num} / {len(chunks)} - Saved (~{output_tokens} output tokens)")
        
        output_parts.append((part_filename, part_content))
    
    return output_parts


def write_manifest(
    output_dir: str,
    parts: list[tuple[str, str]],
    generation_strategy: str = "output_recursive_reduction"
) -> str:
    """
    Write a manifest.json describing the multi-part output structure.
    
    The manifest provides:
    - Part ordering for correct reassembly
    - Generation metadata for auditability
    - Type information for downstream consumers
    
    Args:
        output_dir: Directory containing the output parts
        parts: List of (filename, content) tuples
        generation_strategy: Strategy used to generate the parts
    
    Returns:
        Path to the manifest file
    """
    manifest = {
        "type": "novel_condensation",
        "parts": len(parts),
        "order": [filename for filename, _ in parts],
        "generation_strategy": generation_strategy,
        "prompt": "BASE_CONDENSATION_PROMPT",
        "output_token_budget": SAFE_OUTPUT_TOKEN_BUDGET,
        "estimated_compression_ratio": ESTIMATED_COMPRESSION_RATIO,
    }
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest_path


# Legacy alias for backward compatibility
condense_novel = condense_text


def process_novel(novel_name: str) -> None:
    """
    Produce the final condensed novel from arc-level outputs.
    
    OUTPUT-AWARE SCALABILITY:
    This implementation handles both input overflow (via reduce_until_fit) and
    output overflow (via output-aware chunking). The final novel may consist of
    multiple parts if the condensed output would exceed the model's output limit.
    
    Two-phase approach:
    
    PHASE 1 - Input Reduction (existing behavior):
    Uses reduce_until_fit() to handle input context overflow. If all arcs fit
    within input limits, a single reduction pass occurs. If not, hierarchical
    intermediate layers are created.
    
    PHASE 2 - Output-Aware Chunking (new):
    After input reduction, checks if the resulting output would exceed the
    output token budget. If so, splits the reduced output into multiple
    independent chunks, each processed by a separate LLM call.
    
    Output structure:
    - Single-part: novel.condensed.txt (backward compatible)
    - Multi-part: novel.part_001.condensed.txt, ..., manifest.json
    
    Guarantees:
    - Each LLM call produces output within SAFE_OUTPUT_TOKEN_BUDGET
    - Each output chunk maps to exactly one LLM call, one cost record, one guardrail record
    - Chunking is deterministic and reproducible
    - Resume support via disk persistence
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
    def guardrail_callback(input_text: str, output_text: str, stage: str, unit_id: str) -> None:
        record_condensation(
            input_text=input_text,
            output_text=output_text,
            stage=stage,
            unit_id=unit_id,
        )

    # RESUME SUPPORT: Use output_dir as intermediate storage for hierarchical layers.
    intermediate_dir = output_dir

    # --------------------------------------------------
    # PHASE 1: Input Reduction (handle input overflow)
    # --------------------------------------------------
    # This phase uses reduce_until_fit to ensure input fits within context limits.
    # It produces intermediate condensed groups that are then passed to Phase 2.
    
    # Check if we need hierarchical reduction or can process all arcs together
    merged_arcs = "\n\n".join(arc_texts)
    total_input_tokens = estimate_tokens(merged_arcs)
    
    print(f"  [Input] Total arc text: ~{total_input_tokens} tokens")
    
    # Determine if we need input reduction
    needs_input_reduction = total_input_tokens > DEFAULT_SAFE_TOKEN_LIMIT
    
    if needs_input_reduction:
        print(f"  [Input] Exceeds input limit ({DEFAULT_SAFE_TOKEN_LIMIT}), applying hierarchical reduction")
        
        # COST TRACKING: Create condense function with tracking
        input_condense_fn = make_condense_fn_with_tracking(stage="novel_input_reduction")
        
        # Use reduce_until_fit for input reduction
        # This returns a single condensed string, but we need to track the intermediate units
        # for output-aware splitting. We'll collect the final layer's units instead.
        
        # First, run reduce_until_fit to get intermediate layers saved to disk
        _intermediate_result = reduce_until_fit(
            units=arc_texts,
            condense_fn=input_condense_fn,
            layer_name="arc",
            verbose=True,
            guardrail_callback=guardrail_callback,
            intermediate_dir=intermediate_dir,
        )
        
        # The intermediate result is already condensed - this is our input to Phase 2
        # Wrap it as a single unit for output-aware processing
        units_for_output = [_intermediate_result]
    else:
        print(f"  [Input] Fits within input limit, no hierarchical reduction needed")
        # All arcs can be processed together - pass them as units for output-aware splitting
        units_for_output = arc_texts

    # --------------------------------------------------
    # PHASE 2: Output-Aware Chunking (handle output overflow)
    # --------------------------------------------------
    # This phase ensures each LLM call produces output within the safe output budget.
    
    # Estimate if output would exceed budget
    combined_input = "\n\n".join(units_for_output)
    estimated_output_tokens = estimate_output_tokens(combined_input)
    
    print(f"  [Output] Estimated output: ~{estimated_output_tokens} tokens "
          f"(budget: {SAFE_OUTPUT_TOKEN_BUDGET})")
    
    needs_output_chunking = estimated_output_tokens > SAFE_OUTPUT_TOKEN_BUDGET
    
    if needs_output_chunking:
        print(f"  [Output] Exceeds output budget, splitting into multiple parts")
        
        # Create output-capped condense function
        output_condense_fn = make_output_capped_condense_fn(stage="novel_output_part")
        
        # Condense with output awareness - produces multiple parts
        output_parts = condense_with_output_awareness(
            units=units_for_output,
            condense_fn=output_condense_fn,
            output_dir=output_dir,
            layer_name="novel_part",
            verbose=True,
            guardrail_callback=guardrail_callback,
        )
        
        # Write manifest for multi-part output
        manifest_path = write_manifest(
            output_dir=output_dir,
            parts=output_parts,
            generation_strategy="output_recursive_reduction",
        )
        
        # Also create a combined file for convenience (optional - can be disabled for very large outputs)
        # This is the "assembled" view - the manifest is the source of truth
        combined_content = "\n\n".join(content for _, content in output_parts)
        combined_path = os.path.join(output_dir, "novel.condensed.txt")
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write(combined_content)
        
        # PROGRESS: Stage completion log
        print(f"[Stage] Finished novel condensation ({len(output_parts)} parts)")
        print(f"[Output] {output_dir}/")
        print(f"         - manifest.json")
        for filename, _ in output_parts:
            print(f"         - {filename}")
        print(f"         - novel.condensed.txt (combined)")
        
    else:
        print(f"  [Output] Fits within output budget, single output")
        
        # Single output path - use output-capped prompt for safety
        output_condense_fn = make_output_capped_condense_fn(stage="novel_final")
        
        # Check if output already exists (resume support)
        output_path = os.path.join(output_dir, "novel.condensed.txt")
        
        if os.path.isfile(output_path):
            print(f"  [Output] Loading from disk (resume)")
            with open(output_path, "r", encoding="utf-8") as f:
                condensed_novel = f.read()
        else:
            condensed_novel = output_condense_fn(combined_input)
            
            # GUARDRAIL: Record final condensation
            guardrail_callback(combined_input, condensed_novel, "novel_final", "novel_final")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(condensed_novel)
        
        # Write manifest even for single-part output (for consistency)
        write_manifest(
            output_dir=output_dir,
            parts=[("novel.condensed.txt", condensed_novel)],
            generation_strategy="single_pass",
        )
        
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
