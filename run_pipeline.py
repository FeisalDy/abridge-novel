"""
Abridge Pipeline Orchestrator

Runs the full condensation pipeline in order:
1. Chapter condensation
2. Arc condensation
3. Novel condensation

Guardrails:
- Length ratio monitoring is active throughout the pipeline
- Results are persisted to SQLite for inspection
- Summary is printed at the end of each run

Resume/Skip Flags:
- Use --skip-chapters to reuse existing condensed chapters
- Use --skip-arcs to reuse existing condensed arcs
- Use --skip-novel to reuse existing novel condensation
- Skipping requires explicit flags AND valid existing outputs
- Guardrails remain active for all non-skipped stages
"""

import os
import argparse
from dataclasses import dataclass
from typing import Optional

from chapter_condensation import process_novel as condense_chapters
from arc_condensation import process_novel as condense_arcs
from novel_condensation import process_novel as condense_novel
from guardrails import start_run, end_run, print_run_summary
from cost_tracking import print_usage_summary


# --------------------------------------------------
# Configuration: Expected output directories
# --------------------------------------------------
# These must match the directories used by each condensation module.
# If module paths change, these must be updated accordingly.

RAW_DIR = "data/raw"
CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"
ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"


# --------------------------------------------------
# Skip flags data structure
# --------------------------------------------------

@dataclass
class SkipFlags:
    """
    Explicit skip flags for pipeline stages.
    
    These are TRUST SIGNALS from the user, not automatic optimizations.
    Each flag must be explicitly provided; the pipeline never auto-skips.
    """
    skip_chapters: bool = False
    skip_arcs: bool = False
    skip_novel: bool = False


# --------------------------------------------------
# Validation functions
# --------------------------------------------------

def _count_files(directory: str, suffix: str) -> int:
    """Count files with a given suffix in a directory."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(suffix)])


def validate_chapter_outputs(novel_name: str) -> tuple[bool, str]:
    """
    Validate that condensed chapter outputs exist and are complete.
    
    Checks:
    1. Output directory exists
    2. Number of condensed chapters matches number of raw chapters
    
    Returns:
        (is_valid, message) tuple
    """
    raw_dir = os.path.join(RAW_DIR, novel_name)
    output_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    
    # Check raw directory exists (needed to count expected outputs)
    if not os.path.isdir(raw_dir):
        return False, f"Raw directory not found: {raw_dir}"
    
    # Check output directory exists
    if not os.path.isdir(output_dir):
        return False, f"Condensed chapters directory not found: {output_dir}"
    
    # Count raw chapters and condensed chapters
    raw_count = _count_files(raw_dir, ".txt")
    condensed_count = _count_files(output_dir, ".condensed.txt")
    
    if raw_count == 0:
        return False, f"No raw chapter files found in: {raw_dir}"
    
    if condensed_count == 0:
        return False, f"No condensed chapter files found in: {output_dir}"
    
    if condensed_count != raw_count:
        return False, (
            f"Chapter count mismatch: {raw_count} raw chapters, "
            f"{condensed_count} condensed chapters. "
            f"Cannot safely skip - outputs may be incomplete."
        )
    
    return True, f"Found {condensed_count} condensed chapters (matching {raw_count} raw)"


def validate_arc_outputs(novel_name: str) -> tuple[bool, str]:
    """
    Validate that condensed arc outputs exist.
    
    Checks:
    1. Output directory exists
    2. At least one arc file is present
    
    Note: We cannot easily validate arc count without knowing CHAPTERS_PER_ARC
    and chapter count, so we only check for non-empty output.
    
    Returns:
        (is_valid, message) tuple
    """
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    
    # Check output directory exists
    if not os.path.isdir(output_dir):
        return False, f"Condensed arcs directory not found: {output_dir}"
    
    # Count arc files
    arc_count = _count_files(output_dir, ".condensed.txt")
    
    if arc_count == 0:
        return False, f"No condensed arc files found in: {output_dir}"
    
    return True, f"Found {arc_count} condensed arcs"


def validate_novel_outputs(novel_name: str) -> tuple[bool, str]:
    """
    Validate that the final novel condensation output exists.
    
    Checks:
    1. Output directory exists
    2. novel.condensed.txt file exists
    
    Returns:
        (is_valid, message) tuple
    """
    output_dir = os.path.join(NOVEL_CONDENSED_DIR, novel_name)
    output_file = os.path.join(output_dir, "novel.condensed.txt")
    
    # Check output directory exists
    if not os.path.isdir(output_dir):
        return False, f"Novel condensation directory not found: {output_dir}"
    
    # Check output file exists
    if not os.path.isfile(output_file):
        return False, f"Novel condensation file not found: {output_file}"
    
    # Check file is not empty
    if os.path.getsize(output_file) == 0:
        return False, f"Novel condensation file is empty: {output_file}"
    
    return True, f"Found novel condensation: {output_file}"


# --------------------------------------------------
# Pipeline execution
# --------------------------------------------------

def run_pipeline(
    novel_name: str,
    skip_flags: Optional[SkipFlags] = None,
) -> None:
    """
    Run the condensation pipeline with optional stage skipping.
    
    Args:
        novel_name: Name of the novel (subdirectory under data/raw/)
        skip_flags: Explicit flags indicating which stages to skip.
                   If None, all stages are executed.
    
    IMPORTANT:
    - Skipping is ONLY allowed with explicit flags
    - Skipping requires valid existing outputs (validated before skip)
    - Guardrails remain active for all non-skipped stages
    - The pipeline NEVER auto-skips based on file existence alone
    """
    if skip_flags is None:
        skip_flags = SkipFlags()
    
    # GUARDRAIL: Start a new run to track all condensation events.
    # Each run gets a unique ID for later inspection and regression analysis.
    run_id = start_run()
    print(f"=== Starting pipeline for novel: {novel_name} ===")
    print(f"Guardrail run ID: {run_id}")
    
    # Log skip flags if any are set
    if skip_flags.skip_chapters or skip_flags.skip_arcs or skip_flags.skip_novel:
        print("\nSkip flags active:")
        if skip_flags.skip_chapters:
            print("  --skip-chapters: Will reuse existing condensed chapters")
        if skip_flags.skip_arcs:
            print("  --skip-arcs: Will reuse existing condensed arcs")
        if skip_flags.skip_novel:
            print("  --skip-novel: Will reuse existing novel condensation")

    try:
        # --------------------------------------------------
        # Stage 1: Chapter condensation
        # --------------------------------------------------
        print("\n" + "=" * 50)
        print("[Pipeline] Stage 1/3: Chapter Condensation")
        print("=" * 50)
        
        if skip_flags.skip_chapters:
            # SKIP VALIDATION: Verify outputs exist before allowing skip.
            # This prevents accidental reuse of incomplete or missing data.
            is_valid, message = validate_chapter_outputs(novel_name)
            
            if is_valid:
                print(f"[Skip] Skipping chapter condensation (--skip-chapters)")
                print(f"[Skip] Reusing existing: {message}")
            else:
                # SAFETY: Do not silently proceed with invalid outputs.
                # Raise error to force user to either:
                # 1. Remove the skip flag and regenerate
                # 2. Fix the missing/incomplete outputs manually
                raise ValueError(
                    f"Cannot skip chapters - validation failed: {message}\n"
                    f"Remove --skip-chapters flag to regenerate, or fix outputs manually."
                )
        else:
            condense_chapters(novel_name)

        # --------------------------------------------------
        # Stage 2: Arc condensation
        # --------------------------------------------------
        print("\n" + "=" * 50)
        print("[Pipeline] Stage 2/3: Arc Condensation")
        print("=" * 50)
        
        if skip_flags.skip_arcs:
            # SKIP VALIDATION: Verify outputs exist before allowing skip.
            is_valid, message = validate_arc_outputs(novel_name)
            
            if is_valid:
                print(f"[Skip] Skipping arc condensation (--skip-arcs)")
                print(f"[Skip] Reusing existing: {message}")
            else:
                raise ValueError(
                    f"Cannot skip arcs - validation failed: {message}\n"
                    f"Remove --skip-arcs flag to regenerate, or fix outputs manually."
                )
        else:
            condense_arcs(novel_name)

        # --------------------------------------------------
        # Stage 3: Novel condensation
        # --------------------------------------------------
        print("\n" + "=" * 50)
        print("[Pipeline] Stage 3/3: Novel Condensation")
        print("=" * 50)
        
        if skip_flags.skip_novel:
            # SKIP VALIDATION: Verify outputs exist before allowing skip.
            is_valid, message = validate_novel_outputs(novel_name)
            
            if is_valid:
                print(f"[Skip] Skipping novel condensation (--skip-novel)")
                print(f"[Skip] Reusing existing: {message}")
            else:
                raise ValueError(
                    f"Cannot skip novel - validation failed: {message}\n"
                    f"Remove --skip-novel flag to regenerate, or fix outputs manually."
                )
        else:
            condense_novel(novel_name)

        print("\n" + "=" * 50)
        print(f"[Pipeline] Complete: {novel_name}")
        print("=" * 50)
        
    finally:
        # GUARDRAIL: Always print summary and end run, even if pipeline fails.
        # This ensures partial run data is still visible for debugging.
        print_run_summary(run_id)
        
        # COST TRACKING: Print LLM usage summary at end of run.
        # Shows total tokens and estimated cost for this pipeline execution.
        print_usage_summary(run_id)
        
        end_run()


# --------------------------------------------------
# Command-line interface
# --------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Usage:
        python run_pipeline.py <novel_name> [--skip-chapters] [--skip-arcs] [--skip-novel]
    
    Examples:
        # Run full pipeline
        python run_pipeline.py "Heaven Reincarnation"
        
        # Resume from arc condensation (reuse existing chapters)
        python run_pipeline.py "Heaven Reincarnation" --skip-chapters
        
        # Only regenerate novel condensation
        python run_pipeline.py "Heaven Reincarnation" --skip-chapters --skip-arcs
    """
    parser = argparse.ArgumentParser(
        description="Abridge Pipeline - Hierarchical narrative condensation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Skip Flags (Explicit Resume):
  These flags allow reusing existing outputs from previous runs.
  Each flag requires valid existing outputs - validation is performed before skipping.
  Guardrails remain active for all non-skipped stages.

Examples:
  %(prog)s "My Novel"                          # Full pipeline
  %(prog)s "My Novel" --skip-chapters          # Resume from arc condensation
  %(prog)s "My Novel" --skip-chapters --skip-arcs  # Only novel condensation
        """,
    )
    
    parser.add_argument(
        "novel_name",
        help="Name of the novel (subdirectory under data/raw/)",
    )
    
    parser.add_argument(
        "--skip-chapters",
        action="store_true",
        help="Skip chapter condensation, reuse existing condensed chapters",
    )
    
    parser.add_argument(
        "--skip-arcs",
        action="store_true",
        help="Skip arc condensation, reuse existing condensed arcs",
    )
    
    parser.add_argument(
        "--skip-novel",
        action="store_true",
        help="Skip novel condensation, reuse existing final output",
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    skip_flags = SkipFlags(
        skip_chapters=args.skip_chapters,
        skip_arcs=args.skip_arcs,
        skip_novel=args.skip_novel,
    )
    
    run_pipeline(args.novel_name, skip_flags)
