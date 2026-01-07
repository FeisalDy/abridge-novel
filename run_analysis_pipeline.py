"""
Abridge Analysis Pipeline Orchestrator

This is an ANALYSIS-FIRST orchestrator that reverses the original pipeline.
Structural analysis (Tier-2 and Tier-3) is PRIMARY.
Condensation is OPTIONAL and explicitly invoked.

============================================================
DESIGN PHILOSOPHY
============================================================

The original run_pipeline.py treats condensation as the core workflow,
with analysis as optional add-ons. This orchestrator inverts that model:

ORIGINAL (run_pipeline.py):
    Chapter Condensation → Arc Condensation → Novel Condensation
    → [Optional] Tier-2/3 Analysis

THIS ORCHESTRATOR (run_analysis_pipeline.py):
    Tier-2 Analysis → Tier-3 Analysis
    → [Optional] Condensation Stages

PURPOSE:
The primary value of this pipeline is DECISION SUPPORT — helping readers
determine whether a novel is worth reading in full. Condensation (producing
an abridged version for reading) is secondary.

============================================================
DATA SOURCE FLEXIBILITY
============================================================

Tier-2 and Tier-3 features can operate on:
1. RAW chapters (data/raw/{novel_name}/) — PREFERRED if condensed not available
2. CONDENSED chapters (data/chapters_condensed/{novel_name}/) — used if available

The orchestrator selects the source DETERMINISTICALLY:
- If --prefer-raw is set: use raw chapters
- If --prefer-condensed is set: use condensed chapters (requires they exist)
- If neither: use condensed if available, otherwise raw

This is logged explicitly for auditability.

============================================================
BACKWARD COMPATIBILITY
============================================================

- run_pipeline.py remains fully functional and unchanged
- All existing modules (character_indexing, event_keywords, etc.) are reused
- Module public APIs are preserved
- Existing condensation stages work as before when explicitly invoked

============================================================
EXECUTION ORDER
============================================================

1. Initialize run context (run_id, metadata)
2. Determine data source (RAW vs CONDENSED)
3. [Tier-2] Character Surface Index
4. [Tier-3.1] Character Salience
5. [Tier-3.2] Relationship Signal Matrix
6. [Tier-3.3] Event Keyword Surface Map
7. [Tier-3.4a] Genre Resolver
8. [Tier-3.4b] Tag Resolver
9. [Optional] Chapter Condensation (if --with-chapters)
10. [Optional] Arc Condensation (if --with-arcs)
11. [Optional] Novel Condensation (if --with-novel)
12. Print guardrail summary
13. Print cost summary
14. Generate and save run report
15. End run context

============================================================
CLI USAGE
============================================================

# Full analysis only (default)
python run_analysis_pipeline.py "Novel Name"

# Analysis with condensation
python run_analysis_pipeline.py "Novel Name" --with-chapters --with-arcs --with-novel

# Force raw chapters as source
python run_analysis_pipeline.py "Novel Name" --prefer-raw

# Skip specific analysis stages
python run_analysis_pipeline.py "Novel Name" --skip-salience --skip-relationships
"""

import os
import argparse
from dataclasses import dataclass
from typing import Optional, Literal

from guardrails import start_run, end_run, print_run_summary
from cost_tracking import print_usage_summary
from run_report import (
    init_run_metadata,
    finalize_run_metadata,
    clear_run_metadata,
    generate_and_save_report,
)
from character_indexing import generate_character_index
from character_salience import generate_salience_index
from relationship_matrix import generate_relationship_matrix
from event_keywords import generate_event_keyword_map
from genre_resolver import generate_genre_resolved
from tag_resolver import generate_tag_resolved
from llm.llm_config import LLM_PROVIDER


# --------------------------------------------------
# Configuration: Directory Paths
# --------------------------------------------------

RAW_DIR = "data/raw"
CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"
ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"


# --------------------------------------------------
# Helper: Get model name for current provider
# --------------------------------------------------

def _get_model_name_for_provider() -> str:
    """Get the model name for the current LLM provider."""
    from llm import llm_config
    provider_to_model = {
        "gemini": llm_config.GEMINI_MODEL,
        "deepseek": llm_config.DEEPSEEK_MODEL,
        "vllm": llm_config.VLLM_MODEL,
        "cerebras": llm_config.CEREBRAS_MODEL,
        "groq": llm_config.GROQ_MODEL,
        "copilot": llm_config.COPILOT_MODEL,
        "ollama": llm_config.OLLAMA_MODEL,
    }
    return provider_to_model.get(LLM_PROVIDER, "unknown")


# --------------------------------------------------
# Data Source Type
# --------------------------------------------------

DataSource = Literal["raw", "condensed"]


# --------------------------------------------------
# Analysis Flags Data Structure
# --------------------------------------------------

@dataclass
class AnalysisFlags:
    """
    Flags controlling which analysis stages to run.
    
    By default, ALL analysis stages run. Use skip flags to disable specific stages.
    This is inverted from run_pipeline.py where features are opt-in.
    """
    # Data source preference
    prefer_raw: bool = False
    prefer_condensed: bool = False
    
    # Tier-2 flags (enabled by default)
    skip_character_index: bool = False
    
    # Tier-3 flags (enabled by default)
    skip_salience: bool = False
    skip_relationships: bool = False
    skip_event_keywords: bool = False
    skip_genre_resolver: bool = False
    skip_tag_resolver: bool = False
    
    # Condensation flags (disabled by default — opt-in)
    with_chapters: bool = False
    with_arcs: bool = False
    with_novel: bool = False


# --------------------------------------------------
# Data Source Selection
# --------------------------------------------------

def _count_files(directory: str, suffix: str) -> int:
    """Count files with a given suffix in a directory."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(suffix)])


def determine_data_source(
    novel_name: str,
    flags: AnalysisFlags,
) -> tuple[DataSource, str, str]:
    """
    Determine which data source to use for analysis.
    
    Decision logic:
    1. If --prefer-raw: use raw (fail if not available)
    2. If --prefer-condensed: use condensed (fail if not available)
    3. Otherwise: use condensed if available, else raw
    
    Args:
        novel_name: Name of the novel
        flags: Analysis flags including source preferences
        
    Returns:
        Tuple of (source_type, source_dir, explanation)
        
    Raises:
        ValueError: If preferred source is not available
    """
    raw_dir = os.path.join(RAW_DIR, novel_name)
    condensed_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    
    raw_exists = os.path.isdir(raw_dir) and _count_files(raw_dir, ".txt") > 0
    condensed_exists = os.path.isdir(condensed_dir) and _count_files(condensed_dir, ".condensed.txt") > 0
    
    # Explicit preference: raw
    if flags.prefer_raw:
        if not raw_exists:
            raise ValueError(
                f"--prefer-raw specified but raw chapters not found: {raw_dir}"
            )
        return "raw", raw_dir, "User preference (--prefer-raw)"
    
    # Explicit preference: condensed
    if flags.prefer_condensed:
        if not condensed_exists:
            raise ValueError(
                f"--prefer-condensed specified but condensed chapters not found: {condensed_dir}"
            )
        return "condensed", condensed_dir, "User preference (--prefer-condensed)"
    
    # Auto-select: prefer condensed if available
    if condensed_exists:
        return "condensed", condensed_dir, "Auto-selected (condensed chapters available)"
    
    if raw_exists:
        return "raw", raw_dir, "Auto-selected (only raw chapters available)"
    
    # Neither available
    raise ValueError(
        f"No chapter data found for novel: {novel_name}\n"
        f"Checked: {raw_dir}\n"
        f"Checked: {condensed_dir}"
    )


# --------------------------------------------------
# Validation Functions (for optional condensation)
# --------------------------------------------------

def validate_chapter_outputs(novel_name: str) -> tuple[bool, str]:
    """Validate condensed chapter outputs exist and are complete."""
    raw_dir = os.path.join(RAW_DIR, novel_name)
    output_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    
    if not os.path.isdir(raw_dir):
        return False, f"Raw directory not found: {raw_dir}"
    
    if not os.path.isdir(output_dir):
        return False, f"Condensed chapters directory not found: {output_dir}"
    
    raw_count = _count_files(raw_dir, ".txt")
    condensed_count = _count_files(output_dir, ".condensed.txt")
    
    if raw_count == 0:
        return False, f"No raw chapter files found in: {raw_dir}"
    
    if condensed_count == 0:
        return False, f"No condensed chapter files found in: {output_dir}"
    
    if condensed_count != raw_count:
        return False, (
            f"Chapter count mismatch: {raw_count} raw chapters, "
            f"{condensed_count} condensed chapters."
        )
    
    return True, f"Found {condensed_count} condensed chapters"


def validate_arc_outputs(novel_name: str) -> tuple[bool, str]:
    """Validate condensed arc outputs exist."""
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    
    if not os.path.isdir(output_dir):
        return False, f"Condensed arcs directory not found: {output_dir}"
    
    arc_count = _count_files(output_dir, ".condensed.txt")
    
    if arc_count == 0:
        return False, f"No condensed arc files found in: {output_dir}"
    
    return True, f"Found {arc_count} condensed arcs"


def validate_novel_outputs(novel_name: str) -> tuple[bool, str]:
    """Validate final novel condensation exists."""
    output_dir = os.path.join(NOVEL_CONDENSED_DIR, novel_name)
    output_file = os.path.join(output_dir, "novel.condensed.txt")
    
    if not os.path.isdir(output_dir):
        return False, f"Novel condensation directory not found: {output_dir}"
    
    if not os.path.isfile(output_file):
        return False, f"Novel condensation file not found: {output_file}"
    
    if os.path.getsize(output_file) == 0:
        return False, f"Novel condensation file is empty: {output_file}"
    
    return True, f"Found novel condensation: {output_file}"


# --------------------------------------------------
# Analysis Pipeline Execution
# --------------------------------------------------

def run_analysis_pipeline(
    novel_name: str,
    flags: Optional[AnalysisFlags] = None,
) -> None:
    """
    Run the analysis-first pipeline.
    
    This orchestrator treats structural analysis as primary and condensation
    as optional. Analysis stages can operate on RAW or CONDENSED chapters.
    
    Args:
        novel_name: Name of the novel (subdirectory under data/raw/)
        flags: Analysis flags controlling stage execution and data source
    
    Execution Order:
    1. Tier-2: Character Index (unless --skip-character-index)
    2. Tier-3.1: Salience (unless --skip-salience)
    3. Tier-3.2: Relationships (unless --skip-relationships)
    4. Tier-3.3: Event Keywords (unless --skip-event-keywords)
    5. Tier-3.4a: Genre Resolver (unless --skip-genre-resolver)
    6. Tier-3.4b: Tag Resolver (unless --skip-tag-resolver)
    7. [Optional] Chapter Condensation (if --with-chapters)
    8. [Optional] Arc Condensation (if --with-arcs)
    9. [Optional] Novel Condensation (if --with-novel)
    """
    if flags is None:
        flags = AnalysisFlags()
    
    # GUARDRAIL: Start run tracking
    run_id = start_run()
    print(f"=== Starting ANALYSIS pipeline for novel: {novel_name} ===")
    print(f"Run ID: {run_id}")
    
    # RUN REPORT: Initialize metadata
    metadata = init_run_metadata(run_id, novel_name)
    metadata.llm_provider = LLM_PROVIDER
    metadata.model_name = _get_model_name_for_provider()
    
    try:
        # --------------------------------------------------
        # Data Source Selection
        # --------------------------------------------------
        print("\n" + "=" * 50)
        print("[Pipeline] Determining Data Source")
        print("=" * 50)
        
        source_type, source_dir, source_reason = determine_data_source(novel_name, flags)
        
        # Determine base directory for module calls (modules add novel_name themselves)
        if source_type == "raw":
            base_source_dir = RAW_DIR
        else:
            base_source_dir = CHAPTERS_CONDENSED_DIR
        
        print(f"[Data Source] Type: {source_type.upper()}")
        print(f"[Data Source] Directory: {source_dir}")
        print(f"[Data Source] Reason: {source_reason}")
        
        # Count files for logging
        if source_type == "raw":
            file_count = _count_files(source_dir, ".txt")
            file_suffix = ".txt"
        else:
            file_count = _count_files(source_dir, ".condensed.txt")
            file_suffix = ".condensed.txt"
        print(f"[Data Source] Files: {file_count} chapters ({file_suffix})")
        
        # --------------------------------------------------
        # Log Analysis Stages
        # --------------------------------------------------
        print("\n" + "=" * 50)
        print("[Pipeline] Analysis Stages Configuration")
        print("=" * 50)
        
        # Build list of enabled/disabled stages
        analysis_stages = [
            ("Tier-2: Character Index", not flags.skip_character_index),
            ("Tier-3.1: Character Salience", not flags.skip_salience),
            ("Tier-3.2: Relationship Matrix", not flags.skip_relationships),
            ("Tier-3.3: Event Keywords", not flags.skip_event_keywords),
            ("Tier-3.4a: Genre Resolver", not flags.skip_genre_resolver),
            ("Tier-3.4b: Tag Resolver", not flags.skip_tag_resolver),
        ]
        
        for stage_name, enabled in analysis_stages:
            status = "✓ ENABLED" if enabled else "✗ SKIPPED"
            print(f"  {stage_name}: {status}")
        
        # Log condensation stages
        condensation_stages = [
            ("Chapter Condensation", flags.with_chapters),
            ("Arc Condensation", flags.with_arcs),
            ("Novel Condensation", flags.with_novel),
        ]
        
        print("\n  Optional Condensation:")
        for stage_name, enabled in condensation_stages:
            status = "✓ ENABLED" if enabled else "○ Not requested"
            print(f"    {stage_name}: {status}")
        
        # --------------------------------------------------
        # Tier-2: Character Surface Indexing
        # --------------------------------------------------
        if not flags.skip_character_index:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-2: Character Surface Indexing")
            print("=" * 50)
            # Pass base source directory to character indexing
            generate_character_index(
                novel_name=novel_name,
                run_id=run_id,
                source_dir=base_source_dir,
            )
        
        # --------------------------------------------------
        # Tier-3.1: Character Salience Index
        # --------------------------------------------------
        if not flags.skip_salience:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-3.1: Character Salience Index")
            print("=" * 50)
            generate_salience_index(novel_name, run_id)
        
        # --------------------------------------------------
        # Tier-3.2: Relationship Signal Matrix
        # --------------------------------------------------
        if not flags.skip_relationships:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-3.2: Relationship Signal Matrix")
            print("=" * 50)
            generate_relationship_matrix(novel_name, run_id)
        
        # --------------------------------------------------
        # Tier-3.3: Event Keyword Surface Map
        # --------------------------------------------------
        if not flags.skip_event_keywords:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-3.3: Event Keyword Surface Map")
            print("=" * 50)
            # Pass base source directory to event keywords
            generate_event_keyword_map(
                novel_name=novel_name,
                run_id=run_id,
                source_dir=base_source_dir,
            )
        
        # --------------------------------------------------
        # Tier-3.4a: Genre Resolver
        # --------------------------------------------------
        if not flags.skip_genre_resolver:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-3.4a: Genre Resolver")
            print("=" * 50)
            generate_genre_resolved(novel_name, run_id)
        
        # --------------------------------------------------
        # Tier-3.4b: Tag Resolver
        # --------------------------------------------------
        if not flags.skip_tag_resolver:
            print("\n" + "=" * 50)
            print("[Pipeline] Tier-3.4b: Tag Resolver")
            print("=" * 50)
            generate_tag_resolved(novel_name, run_id)
        
        # --------------------------------------------------
        # Optional: Condensation Stages
        # --------------------------------------------------
        if flags.with_chapters or flags.with_arcs or flags.with_novel:
            print("\n" + "=" * 50)
            print("[Pipeline] Optional Condensation Stages")
            print("=" * 50)
            
            # Import condensation modules only if needed
            from chapter_condensation import process_novel as condense_chapters
            from arc_condensation import process_novel as condense_arcs
            from novel_condensation import process_novel as condense_novel
            
            # Chapter Condensation
            if flags.with_chapters:
                print("\n[Condensation] Stage 1: Chapter Condensation")
                condense_chapters(novel_name)
                metadata.chapters_count = _count_files(
                    os.path.join(CHAPTERS_CONDENSED_DIR, novel_name),
                    ".condensed.txt"
                )
            
            # Arc Condensation
            if flags.with_arcs:
                # Validate chapters exist first
                is_valid, msg = validate_chapter_outputs(novel_name)
                if not is_valid:
                    print(f"[Condensation] ⚠️ Cannot run arc condensation: {msg}")
                    print("[Condensation] Skipping arc condensation (requires condensed chapters)")
                else:
                    print("\n[Condensation] Stage 2: Arc Condensation")
                    condense_arcs(novel_name)
                    metadata.arcs_count = _count_files(
                        os.path.join(ARCS_CONDENSED_DIR, novel_name),
                        ".condensed.txt"
                    )
            
            # Novel Condensation
            if flags.with_novel:
                # Validate arcs exist first
                is_valid, msg = validate_arc_outputs(novel_name)
                if not is_valid:
                    print(f"[Condensation] ⚠️ Cannot run novel condensation: {msg}")
                    print("[Condensation] Skipping novel condensation (requires condensed arcs)")
                else:
                    print("\n[Condensation] Stage 3: Novel Condensation")
                    condense_novel(novel_name)
        
        print("\n" + "=" * 50)
        print(f"[Pipeline] Complete: {novel_name}")
        print("=" * 50)
        
    finally:
        # GUARDRAIL: Always print summaries, even on failure
        print_run_summary(run_id)
        
        # COST TRACKING: Print usage summary
        print_usage_summary(run_id)
        
        # RUN REPORT: Generate unified report
        finalized_metadata = finalize_run_metadata()
        generate_and_save_report(run_id, novel_name, finalized_metadata)
        clear_run_metadata()
        
        end_run()


# --------------------------------------------------
# Command-Line Interface
# --------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Usage:
        python run_analysis_pipeline.py <novel_name> [options]
    
    Examples:
        # Full analysis (default)
        python run_analysis_pipeline.py "Heaven Reincarnation"
        
        # Analysis with condensation
        python run_analysis_pipeline.py "Heaven Reincarnation" --with-chapters --with-arcs --with-novel
        
        # Force raw chapters
        python run_analysis_pipeline.py "Heaven Reincarnation" --prefer-raw
        
        # Skip specific stages
        python run_analysis_pipeline.py "Heaven Reincarnation" --skip-relationships --skip-genre-resolver
    """
    parser = argparse.ArgumentParser(
        description="Abridge Analysis Pipeline - Structural analysis with optional condensation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ANALYSIS-FIRST DESIGN:
  This pipeline treats structural analysis (Tier-2/3) as PRIMARY.
  Condensation is OPTIONAL and must be explicitly requested.

DATA SOURCE:
  By default, uses condensed chapters if available, otherwise raw chapters.
  Use --prefer-raw or --prefer-condensed to override.

Examples:
  %(prog)s "My Novel"                          # Full analysis only
  %(prog)s "My Novel" --prefer-raw             # Force raw chapters
  %(prog)s "My Novel" --with-chapters          # Analysis + condensation
  %(prog)s "My Novel" --skip-salience          # Skip salience computation
        """,
    )
    
    parser.add_argument(
        "novel_name",
        help="Name of the novel (subdirectory under data/raw/)",
    )
    
    # Data source preference
    source_group = parser.add_argument_group("Data Source")
    source_mutex = source_group.add_mutually_exclusive_group()
    source_mutex.add_argument(
        "--prefer-raw",
        action="store_true",
        help="Force analysis on raw chapters (error if not available)",
    )
    source_mutex.add_argument(
        "--prefer-condensed",
        action="store_true",
        help="Force analysis on condensed chapters (error if not available)",
    )
    
    # Analysis skip flags
    analysis_group = parser.add_argument_group("Analysis Stages (skip flags)")
    analysis_group.add_argument(
        "--skip-character-index",
        action="store_true",
        help="Skip Tier-2 character surface indexing",
    )
    analysis_group.add_argument(
        "--skip-salience",
        action="store_true",
        help="Skip Tier-3.1 character salience computation",
    )
    analysis_group.add_argument(
        "--skip-relationships",
        action="store_true",
        help="Skip Tier-3.2 relationship signal matrix",
    )
    analysis_group.add_argument(
        "--skip-event-keywords",
        action="store_true",
        help="Skip Tier-3.3 event keyword scanning",
    )
    analysis_group.add_argument(
        "--skip-genre-resolver",
        action="store_true",
        help="Skip Tier-3.4a genre resolution",
    )
    analysis_group.add_argument(
        "--skip-tag-resolver",
        action="store_true",
        help="Skip Tier-3.4b tag resolution",
    )
    
    # Condensation opt-in flags
    condensation_group = parser.add_argument_group("Optional Condensation (opt-in)")
    condensation_group.add_argument(
        "--with-chapters",
        action="store_true",
        help="Enable chapter condensation after analysis",
    )
    condensation_group.add_argument(
        "--with-arcs",
        action="store_true",
        help="Enable arc condensation after analysis (requires --with-chapters or existing)",
    )
    condensation_group.add_argument(
        "--with-novel",
        action="store_true",
        help="Enable novel condensation after analysis (requires --with-arcs or existing)",
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    flags = AnalysisFlags(
        prefer_raw=args.prefer_raw,
        prefer_condensed=args.prefer_condensed,
        skip_character_index=args.skip_character_index,
        skip_salience=args.skip_salience,
        skip_relationships=args.skip_relationships,
        skip_event_keywords=args.skip_event_keywords,
        skip_genre_resolver=args.skip_genre_resolver,
        skip_tag_resolver=args.skip_tag_resolver,
        with_chapters=args.with_chapters,
        with_arcs=args.with_arcs,
        with_novel=args.with_novel,
    )
    
    run_analysis_pipeline(args.novel_name, flags)
