"""
    TODO: Refactor this docstring by following the PEP 257 standard
    chapter_condensation.py is responsible for turning raw novel chapters into condensed chapters,
    faithfully and deterministically, using the base condensation prompt.

    Responsibilities:
    1. Input Handling
        - Load raw chapter text files
        - Preserve chapter order
        - Treat each chapter as an independent unit
    2. Condensation Execution
        - Inject each chapter’s text into BASE_CONDENSATION_PROMPT
        - Send the prompt to the LLM
        - Receive the condensed output
    3. Output Handling
        - Save each condensed chapter as a separate file
        - Ensure outputs correspond 1:1 with inputs
        - Never overwrite raw chapter files
    4. Determinism & Repeatability
        - Given the same input and prompt version, behavior should be reproducible
        - Output order must match input order

    Non-Responsibilities:
    1. Structural Interpretation
        - Detect scenes
        - Detect story arcs
        - Reorder content
        - Merge chapters
    2. Semantic Interpretation
        - Judge importance
        - Decide what is “major” or “minor”
        - Add opinions or commentary
        - Inject genre or metadata
    3. Post Processing Intelligence
        - No validation of plot completeness
        - No consistency checking
        - No character tracking
        - No summarization of summaries
    4. Pipeline Progression
        - It must not trigger arc condensation
        - It must not handle multi-stage logic
        - It must not coordinate later steps
    5. UI/UX Considerations
        - No interactive interface
        - No progress bars (optional logging is fine)
        - No user-facing configuration logic

    Error Handling Scope
        - May fail loudly if input is invalid
        - May retry or log LLM failures
        - Must not attempt semantic recovery
    If condensation fails, the chapter fails — it is not silently skipped.

    Think this module as a conveyor belt that takes in raw chapters and produces edited chapters,
    without understanding the story beyond what the editor prompt enforces.
"""
import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm
from guardrails import record_condensation
from cost_tracking import record_llm_usage
from prefilter import prefilter_chapter, PrefilterResult

# --------------------------------------------------
# Configuration
# --------------------------------------------------

llm = create_llm()

RAW_BASE_DIR = "data/raw"
OUTPUT_BASE_DIR = "data/chapters_condensed"


# Maximum retries for LLM calls before failing
MAX_LLM_RETRIES = 3


def run_llm(prompt: str, stage: str = "chapter", unit_id: str = "") -> str:
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

def condense_chapter(chapter_text: str, unit_id: str = "") -> tuple[str, PrefilterResult | None]:
    """
    Apply deterministic pre-filtering and then LLM condensation to a chapter.
    
    Pre-filtering removes non-plot paragraphs (those with no named entities,
    no dialogue, and no past-tense verbs) BEFORE sending to the LLM.
    This reduces token costs and noise.
    
    Args:
        chapter_text: The raw chapter text to condense
        unit_id: Identifier for cost tracking (e.g., "chapter_001")
    
    Returns:
        Tuple of (condensed_text, prefilter_result).
        prefilter_result contains statistics about what was filtered.
    
    Raises:
        RuntimeError: If LLM fails after all retries.
    """
    # STEP 1: Deterministic pre-filtering (language-aware)
    # Remove paragraphs that have no plot-relevant signals.
    # This is a STRUCTURAL operation, not semantic interpretation.
    # NOTE: Filtering is ONLY applied to English text. Non-English passes through unchanged.
    prefilter_result = prefilter_chapter(chapter_text)
    
    # Log pre-filter statistics
    if not prefilter_result.filtering_applied:
        print(f"  [prefilter] Skipped (non-English text detected: {prefilter_result.detected_language})")
    elif prefilter_result.dropped_paragraph_count > 0:
        print(f"  [prefilter] Dropped {prefilter_result.dropped_paragraph_count}/{prefilter_result.original_paragraph_count} paragraphs ({prefilter_result.drop_ratio:.1%})")
    
    # Use filtered text for LLM condensation
    text_for_llm = prefilter_result.filtered_text
    
    # STEP 2: LLM condensation on filtered text
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text_for_llm
    )
    condensed_text = run_llm(prompt, stage="chapter", unit_id=unit_id)
    
    return condensed_text, prefilter_result


def process_novel(novel_name: str) -> None:
    """
    Condense all chapters of a novel.
    """
    raw_dir = os.path.join(RAW_BASE_DIR, novel_name)
    output_dir = os.path.join(OUTPUT_BASE_DIR, novel_name)

    if not os.path.isdir(raw_dir):
        raise ValueError(f"Raw novel directory not found: {raw_dir}")

    os.makedirs(output_dir, exist_ok=True)

    chapters = sorted(
        f for f in os.listdir(raw_dir)
        if f.endswith(".txt")
    )

    if not chapters:
        raise ValueError("No chapter files found")

    # PROGRESS: Report total count at stage start for visibility
    total_chapters = len(chapters)
    print(f"[Stage] Starting chapter condensation ({total_chapters} chapters)")
    
    # Track aggregate pre-filter statistics
    total_original_paragraphs = 0
    total_dropped_paragraphs = 0

    for chapter_index, filename in enumerate(chapters, start=1):
        input_path = os.path.join(raw_dir, filename)
        output_filename = filename.replace(".txt", ".condensed.txt")
        output_path = os.path.join(output_dir, output_filename)

        # PROGRESS: Per-unit progress log showing current index and total
        print(f"[Chapter] {chapter_index} / {total_chapters} - {filename}")

        with open(input_path, "r", encoding="utf-8") as f:
            chapter_text = f.read()

        # Cost tracking unit ID derived from filename
        unit_id = filename.replace(".txt", "")
        
        # Condense the chapter (with pre-filtering) - will retry on failure, raises on final failure
        condensed_text, prefilter_result = condense_chapter(chapter_text, unit_id=unit_id)
        
        # Accumulate pre-filter statistics
        if prefilter_result:
            total_original_paragraphs += prefilter_result.original_paragraph_count
            total_dropped_paragraphs += prefilter_result.dropped_paragraph_count

        # GUARDRAIL: Record compression ratio for this chapter.
        # This is observational only - does not modify output or block execution.
        # NOTE: We record against the ORIGINAL text, not pre-filtered, for accurate ratio.
        record_condensation(
            input_text=chapter_text,
            output_text=condensed_text,
            stage="chapter",
            unit_id=unit_id,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(condensed_text)

    # PROGRESS: Stage completion log with pre-filter summary
    print(f"[Stage] Finished chapter condensation ({total_chapters} chapters)")
    if total_original_paragraphs > 0:
        overall_drop_ratio = total_dropped_paragraphs / total_original_paragraphs
        print(f"[prefilter] Total: dropped {total_dropped_paragraphs}/{total_original_paragraphs} paragraphs ({overall_drop_ratio:.1%})")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python chapter_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)