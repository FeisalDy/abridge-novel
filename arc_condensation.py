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
# Resume Detection (Arc-Level)
# --------------------------------------------------
# Arcs use ADAPTIVE grouping based on chapter count:
# - Input: condensed chapters from data/chapters_condensed/{novel}/
# - Output: arc files data/arcs_condensed/{novel}/arc_XX.condensed.txt
#
# Resume logic (ADAPTIVE):
# - Enumerate all condensed chapter files
# - Calculate expected total arcs based on CHAPTERS_PER_ARC
# - Enumerate existing arc output files
# - Detect which arc indices are missing
# - Process ONLY missing arcs
# - Never overwrite existing arc outputs

def get_arc_filename(arc_index: int) -> str:
    """Generate deterministic arc filename from index."""
    return f"arc_{arc_index:02d}.condensed.txt"


def get_arc_index_from_filename(filename: str) -> int | None:
    """Extract arc index from filename, or None if invalid format."""
    import re
    match = re.match(r"arc_(\d+)\.condensed\.txt$", filename)
    if match:
        return int(match.group(1))
    return None


def compute_arc_ranges(chapter_files: list[str], chapters_per_arc: int) -> list[tuple[int, list[str]]]:
    """
    Compute deterministic arc groupings from chapter files.
    
    Returns list of (arc_index, chapter_files) tuples.
    Arc indices are 1-based.
    """
    arcs = []
    arc_index = 1
    
    for i in range(0, len(chapter_files), chapters_per_arc):
        arc_chapters = chapter_files[i:i + chapters_per_arc]
        arcs.append((arc_index, arc_chapters))
        arc_index += 1
    
    return arcs


def detect_missing_arcs(novel_name: str) -> tuple[list[tuple[int, list[str]]], list[int], list[int]]:
    """
    Detect which arcs are missing outputs (need processing).
    
    ADAPTIVE RULE: Arcs are derived groupings - we compute expected arcs
    from chapter count, then check which arc outputs exist.
    
    Args:
        novel_name: Name of the novel (subdirectory name)
    
    Returns:
        Tuple of (all_arcs, done_arc_indices, missing_arc_indices) where:
        - all_arcs: List of (arc_index, chapter_files) tuples
        - done_arc_indices: Arc indices with existing valid outputs
        - missing_arc_indices: Arc indices without outputs (need processing)
    
    Raises:
        ValueError: If input directory doesn't exist or has no chapters
    """
    input_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    
    if not os.path.isdir(input_dir):
        raise ValueError(f"Condensed chapters directory not found: {input_dir}")
    
    # Enumerate all condensed chapter files (sorted for deterministic grouping)
    chapter_files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".condensed.txt")
    )
    
    if not chapter_files:
        raise ValueError(f"No condensed chapter files found in {input_dir}")
    
    # Compute expected arcs from chapter count
    all_arcs = compute_arc_ranges(chapter_files, CHAPTERS_PER_ARC)
    
    # Enumerate existing arc output files
    existing_arc_indices = set()
    if os.path.isdir(output_dir):
        for filename in os.listdir(output_dir):
            arc_idx = get_arc_index_from_filename(filename)
            if arc_idx is not None:
                # Verify output file is non-empty (corruption check)
                output_path = os.path.join(output_dir, filename)
                if os.path.getsize(output_path) > 0:
                    existing_arc_indices.add(arc_idx)
    
    # Classify arcs as done or missing
    expected_arc_indices = {arc_idx for arc_idx, _ in all_arcs}
    done_arc_indices = sorted(existing_arc_indices & expected_arc_indices)
    missing_arc_indices = sorted(expected_arc_indices - existing_arc_indices)
    
    return all_arcs, done_arc_indices, missing_arc_indices


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm(stage="arc")

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
    
    RESUME SUPPORT:
    This function automatically detects and resumes interrupted runs.
    - Arcs with existing valid outputs are skipped (never reprocessed)
    - Only missing arcs are processed
    - Existing outputs are never overwritten
    - Arc grouping is deterministic based on CHAPTERS_PER_ARC
    
    The resume check is idempotent: running multiple times produces the same result.
    """
    input_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)

    # RESUME DETECTION: Identify which arcs need processing
    all_arcs, done_arc_indices, missing_arc_indices = detect_missing_arcs(novel_name)

    os.makedirs(output_dir, exist_ok=True)

    total_arcs = len(all_arcs)
    done_count = len(done_arc_indices)
    missing_count = len(missing_arc_indices)
    total_chapters = sum(len(chapters) for _, chapters in all_arcs)
    
    # PROGRESS: Report resume state at stage start
    if done_count > 0 and missing_count > 0:
        # Partial completion detected - resuming
        print(f"[Stage] Resuming arc condensation")
        print(f"  [Resume] {done_count}/{total_arcs} arcs already done")
        print(f"  [Resume] {missing_count} arcs remaining")
    elif done_count == total_arcs:
        # All arcs already done - nothing to process
        print(f"[Stage] Arc condensation already complete ({total_arcs} arcs from {total_chapters} chapters)")
        print(f"  [Resume] All outputs exist, skipping stage")
        return
    else:
        # Fresh start - no existing outputs
        print(f"[Stage] Starting arc condensation ({total_arcs} arcs from {total_chapters} chapters)")
    
    # Build lookup for arc data by index
    arc_data_by_index = {arc_idx: chapters for arc_idx, chapters in all_arcs}

    # Process only missing arcs (resume-safe)
    for processed_idx, arc_index in enumerate(missing_arc_indices, start=1):
        arc_chapters = arc_data_by_index[arc_index]

        # PROGRESS: Per-unit progress log showing:
        # - Arc position in full list (for context)
        # - Progress within current batch (for resume tracking)
        print(f"[Arc] {arc_index}/{total_arcs} ({len(arc_chapters)} chapters) (batch {processed_idx}/{missing_count})")
        
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

        output_filename = get_arc_filename(arc_index)
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(condensed_arc)

    # PROGRESS: Stage completion log
    if missing_count > 0:
        print(f"[Stage] Finished arc condensation ({missing_count} processed, {total_arcs} total)")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python arc_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)
