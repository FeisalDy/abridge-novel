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

llm = create_llm(stage="chapter")

RAW_BASE_DIR = "data/raw"
OUTPUT_BASE_DIR = "data/chapters_condensed"


# Maximum retries for LLM calls before failing
MAX_LLM_RETRIES = 3


# --------------------------------------------------
# Resume Detection (Chapter-Level)
# --------------------------------------------------
# Chapters use STRICT 1:1 mapping:
# - Input: data/raw/{novel}/{filename}.txt
# - Output: data/chapters_condensed/{novel}/{filename}.condensed.txt
#
# Resume logic:
# - Enumerate all raw chapter files
# - Enumerate all condensed output files
# - Compare by deterministic identifier (filename stem)
# - Process ONLY missing chapters (those without corresponding output)
# - Never overwrite existing outputs
# - Never reprocess completed chapters

def get_expected_output_filename(input_filename: str) -> str:
    """Convert input filename to expected output filename."""
    return input_filename.replace(".txt", ".condensed.txt")


def get_input_filename_from_output(output_filename: str) -> str:
    """Convert output filename back to input filename."""
    return output_filename.replace(".condensed.txt", ".txt")


def detect_missing_chapters(novel_name: str) -> tuple[list[str], list[str], list[str]]:
    """
    Detect which chapters are missing outputs (need processing).
    
    STRICT 1:1 RULE: Each raw chapter must have exactly one condensed output.
    
    Args:
        novel_name: Name of the novel (subdirectory name)
    
    Returns:
        Tuple of (all_chapters, done_chapters, missing_chapters) where:
        - all_chapters: All raw chapter filenames (sorted)
        - done_chapters: Chapters with existing valid outputs
        - missing_chapters: Chapters without outputs (need processing)
    
    Raises:
        ValueError: If input directory doesn't exist or has no chapters
    """
    raw_dir = os.path.join(RAW_BASE_DIR, novel_name)
    output_dir = os.path.join(OUTPUT_BASE_DIR, novel_name)
    
    if not os.path.isdir(raw_dir):
        raise ValueError(f"Raw novel directory not found: {raw_dir}")
    
    # Enumerate all raw chapter files (sorted for deterministic order)
    all_chapters = sorted(
        f for f in os.listdir(raw_dir)
        if f.endswith(".txt")
    )
    
    if not all_chapters:
        raise ValueError(f"No chapter files found in {raw_dir}")
    
    # Enumerate existing output files
    existing_outputs = set()
    if os.path.isdir(output_dir):
        existing_outputs = set(
            f for f in os.listdir(output_dir)
            if f.endswith(".condensed.txt")
        )
    
    # Classify chapters as done or missing
    done_chapters = []
    missing_chapters = []
    
    for chapter_file in all_chapters:
        expected_output = get_expected_output_filename(chapter_file)
        if expected_output in existing_outputs:
            # Verify output file is non-empty (corruption check)
            output_path = os.path.join(output_dir, expected_output)
            if os.path.getsize(output_path) > 0:
                done_chapters.append(chapter_file)
            else:
                # Empty output = corrupted, needs reprocessing
                missing_chapters.append(chapter_file)
        else:
            missing_chapters.append(chapter_file)
    
    return all_chapters, done_chapters, missing_chapters


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
    
    RESUME SUPPORT:
    This function automatically detects and resumes interrupted runs.
    - Chapters with existing valid outputs are skipped (never reprocessed)
    - Only missing chapters are processed
    - Existing outputs are never overwritten
    - Processing order is preserved (sorted by filename)
    
    The resume check is idempotent: running multiple times produces the same result.
    """
    raw_dir = os.path.join(RAW_BASE_DIR, novel_name)
    output_dir = os.path.join(OUTPUT_BASE_DIR, novel_name)

    # RESUME DETECTION: Identify which chapters need processing
    all_chapters, done_chapters, missing_chapters = detect_missing_chapters(novel_name)
    
    os.makedirs(output_dir, exist_ok=True)
    
    total_chapters = len(all_chapters)
    done_count = len(done_chapters)
    missing_count = len(missing_chapters)
    
    # PROGRESS: Report resume state at stage start
    if done_count > 0 and missing_count > 0:
        # Partial completion detected - resuming
        print(f"[Stage] Resuming chapter condensation")
        print(f"  [Resume] {done_count}/{total_chapters} chapters already done")
        print(f"  [Resume] {missing_count} chapters remaining")
    elif done_count == total_chapters:
        # All chapters already done - nothing to process
        print(f"[Stage] Chapter condensation already complete ({total_chapters} chapters)")
        print(f"  [Resume] All outputs exist, skipping stage")
        return
    else:
        # Fresh start - no existing outputs
        print(f"[Stage] Starting chapter condensation ({total_chapters} chapters)")
    
    # Only process missing chapters (resume-safe)
    chapters_to_process = missing_chapters
    
    # Track aggregate pre-filter statistics
    total_original_paragraphs = 0
    total_dropped_paragraphs = 0
    
    # Track progress across the entire set (for consistent numbering)
    # Map each chapter to its position in the full sorted list
    chapter_positions = {ch: idx + 1 for idx, ch in enumerate(all_chapters)}

    for processed_idx, filename in enumerate(chapters_to_process, start=1):
        input_path = os.path.join(raw_dir, filename)
        output_filename = get_expected_output_filename(filename)
        output_path = os.path.join(output_dir, output_filename)
        
        # Get the chapter's position in the full ordered list
        chapter_position = chapter_positions[filename]

        # PROGRESS: Per-unit progress log showing:
        # - Position in full chapter list (for context)
        # - Progress within current batch (for resume tracking)
        print(f"[Chapter] {chapter_position}/{total_chapters} - {filename} (batch {processed_idx}/{missing_count})")

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
    if missing_count > 0:
        print(f"[Stage] Finished chapter condensation ({missing_count} processed, {total_chapters} total)")
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