import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm
from guardrails import record_condensation
from cost_tracking import record_llm_usage

# --------------------------------------------------
# Configuration
# --------------------------------------------------

CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"
ARCS_CONDENSED_DIR = "data/arcs_condensed"

CHAPTERS_PER_ARC = 10


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm()

# Maximum retries for LLM calls before failing
MAX_LLM_RETRIES = 3


def run_llm(prompt: str, stage: str = "arc", unit_id: str = "") -> str:
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

def condense_arc(text: str, unit_id: str = "") -> str:
    """
    Apply the base condensation prompt to merged chapter text.
    
    Args:
        text: The merged chapter text to condense
        unit_id: Identifier for cost tracking (e.g., "arc_01")
    
    Returns:
        The condensed arc text.
    
    Raises:
        RuntimeError: If LLM fails after all retries.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text
    )
    return run_llm(prompt, stage="arc", unit_id=unit_id)


def process_novel(novel_name: str) -> None:
    """
    Condense chapter-level outputs into arc-level outputs.
    """
    input_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)

    if not os.path.isdir(input_dir):
        raise ValueError(f"Condensed chapters directory not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    chapter_files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".condensed.txt")
    )

    if not chapter_files:
        raise ValueError("No condensed chapter files found")

    # PROGRESS: Calculate total arcs and report at stage start
    total_arcs = (len(chapter_files) + CHAPTERS_PER_ARC - 1) // CHAPTERS_PER_ARC
    print(f"[Stage] Starting arc condensation ({total_arcs} arcs from {len(chapter_files)} chapters)")

    arc_index = 1

    for i in range(0, len(chapter_files), CHAPTERS_PER_ARC):
        arc_chapters = chapter_files[i:i + CHAPTERS_PER_ARC]

        # PROGRESS: Per-unit progress log showing current index and total
        print(f"[Arc] {arc_index} / {total_arcs} ({len(arc_chapters)} chapters)")
        
        unit_id = f"arc_{arc_index:02d}"

        merged_text_parts = []

        for filename in arc_chapters:
            path = os.path.join(input_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                merged_text_parts.append(f.read())

        merged_text = "\n\n".join(merged_text_parts)

        # Condense the arc - will retry on failure, raises on final failure
        condensed_arc = condense_arc(merged_text, unit_id=unit_id)

        # GUARDRAIL: Record compression ratio for this arc.
        # This is observational only - does not modify output or block execution.
        record_condensation(
            input_text=merged_text,
            output_text=condensed_arc,
            stage="arc",
            unit_id=unit_id,
        )

        output_filename = f"arc_{arc_index:02d}.condensed.txt"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(condensed_arc)

        arc_index += 1

    # PROGRESS: Stage completion log
    print(f"[Stage] Finished arc condensation ({total_arcs} arcs)")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python arc_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)
