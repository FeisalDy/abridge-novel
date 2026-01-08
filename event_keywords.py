"""
Event Keyword Surface Map for Abridge Pipeline (Tier-3.3)

PURPOSE:
This module extracts LEXICAL SIGNALS for event-related keywords from the
condensed novel text. It records WHERE and HOW OFTEN specific keywords
appear — it does NOT confirm events occurred or assign meaning.

============================================================
WHAT THIS IS
============================================================

This is a LEXICAL, OBSERVATIONAL feature that:
- Detects occurrences of predefined event keywords/phrases
- Records frequency, distribution, and persistence metrics
- Produces a neutral, queryable signal map

============================================================
WHAT THIS IS NOT (CRITICAL)
============================================================

This feature DOES NOT:
- Confirm that events actually happened in the story
- Assign meaning or interpretation to keyword presence
- Resolve contradictions or ambiguity
- Tag genres or categories
- Correlate keywords with characters
- Use semantic similarity or LLMs

Keyword presence is LEXICAL EVIDENCE, not narrative assertion.
The word "death" appearing does not mean someone died.

============================================================
KEYWORD DICTIONARY
============================================================

The keyword dictionary is:
- Manually curated and static
- Versioned for reproducibility
- Declarative (explicit terms, no inference)
- Supports multi-word phrases and aliases

Dictionary format:
{
  "keyword_id": {
    "terms": ["primary term", "alias1", "alias2"],
    "category": "optional_category_for_grouping"
  }
}

============================================================
MATCHING RULES (DOCUMENTED)
============================================================

1. Case-insensitive matching
2. Word-boundary aware (prevents partial matches)
3. Multi-word phrases supported
4. All terms in a group contribute to the same keyword_id
5. Deterministic: same input always produces same output

============================================================
SIGNAL DEFINITIONS
============================================================

For each keyword:
- mentions: Total count across all chapters
- first_seen_unit: Index of first chapter with keyword (0-based)
- last_seen_unit: Index of last chapter with keyword (0-based)
- narrative_spread: (last_seen - first_seen + 1) chapters
- density: mentions / total_chapters
- chapters_present: List of chapter indices where keyword appears
- matched_terms: Which specific terms from the group were found

============================================================
CONSUMER WARNING
============================================================

Downstream consumers MUST understand:
- Keyword presence ≠ event confirmation
- High frequency ≠ narrative importance
- This is lexical surface data, not story understanding
- Use for pattern detection, not plot summarization

============================================================
STORAGE
============================================================

Map data is stored per run_id in:
- JSON artifact: data/event_keywords/{novel_name}/{run_id}.event_keywords.json

Includes dictionary version for reproducibility.
"""

import os
import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict
from dotenv import load_dotenv
from dict.event_keyword_dictionary import KEYWORD_DICTIONARY_VERSION, KEYWORD_DICTIONARY
load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------

EVENT_KEYWORDS_DIR = os.getenv(
    "ABRIDGE_EVENT_KEYWORDS_DIR",
    "data/event_keywords"
)

CHAPTERS_CONDENSED_DIR = os.getenv(
    "ABRIDGE_CHAPTERS_CONDENSED_DIR",
    "data/chapters_condensed"
)

# Raw chapters directory (for analysis-first pipeline)
RAW_CHAPTERS_DIR = os.getenv(
    "ABRIDGE_RAW_CHAPTERS_DIR",
    "data/raw"
)

# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class KeywordSignal:
    """
    Surface-level signal data for a single keyword/keyword group.
    
    WARNING: This is LEXICAL data, not event confirmation.
    Keyword presence does NOT mean an event occurred.
    """
    keyword_id: str
    category: str
    
    # Terms that were actually matched
    matched_terms: list[str] = field(default_factory=list)
    
    # Raw metrics
    mentions: int = 0
    first_seen_unit: int = -1  # -1 means never seen
    last_seen_unit: int = -1
    
    # Derived metrics
    narrative_spread: int = 0  # last - first + 1
    density: float = 0.0       # mentions / total_chapters
    
    # Distribution detail
    chapters_present: list[int] = field(default_factory=list)
    mentions_per_chapter: dict[int, int] = field(default_factory=dict)


@dataclass
class EventKeywordSurfaceMap:
    """
    Complete event keyword surface map for a novel run.
    
    This is a TIER-3.3 DERIVED ARTIFACT.
    It records lexical signals, NOT event confirmations.
    """
    # Identification
    novel_name: str
    run_id: str
    tier: str = "tier-3.3"
    
    # Dictionary version for reproducibility
    dictionary_version: str = KEYWORD_DICTIONARY_VERSION
    
    # Novel metadata
    total_chapters: int = 0
    total_keywords_searched: int = 0
    total_keywords_found: int = 0
    total_mentions: int = 0
    
    # Keyword signals (keyed by keyword_id)
    keywords: dict[str, KeywordSignal] = field(default_factory=dict)
    
    # Category summary (category -> list of keyword_ids found)
    categories_found: dict[str, list[str]] = field(default_factory=dict)
    
    # Warnings for downstream consumers
    warnings: list[str] = field(default_factory=lambda: [
        "Keyword presence does NOT confirm event occurrence",
        "High frequency does NOT indicate narrative importance",
        "This is lexical surface data, not story understanding",
        "Use for pattern detection, not plot summarization",
    ])


# --------------------------------------------------
# Keyword Matching
# --------------------------------------------------

def _compile_keyword_patterns(
    dictionary: dict,
) -> dict[str, tuple[list[re.Pattern], str]]:
    """
    Compile regex patterns for all keywords in dictionary.
    
    Returns dict mapping keyword_id -> (list of compiled patterns, category)
    
    Pattern rules:
    - Case-insensitive
    - Word-boundary aware (\\b)
    - Multi-word phrases supported
    """
    compiled = {}
    
    for keyword_id, config in dictionary.items():
        terms = config.get("terms", [])
        category = config.get("category", "uncategorized")
        
        patterns = []
        for term in terms:
            # Escape special regex chars, then add word boundaries
            escaped = re.escape(term)
            # Use word boundaries for whole-word matching
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            patterns.append(pattern)
        
        compiled[keyword_id] = (patterns, category)
    
    return compiled


def _match_keywords_in_text(
    text: str,
    patterns: dict[str, tuple[list[re.Pattern], str]],
) -> dict[str, tuple[int, set[str]]]:
    """
    Match all keywords in text and return counts.
    
    Returns dict mapping keyword_id -> (count, set of matched terms)
    """
    results = {}
    
    for keyword_id, (pattern_list, category) in patterns.items():
        total_count = 0
        matched_terms = set()
        
        for pattern in pattern_list:
            matches = pattern.findall(text)
            if matches:
                total_count += len(matches)
                # Extract the original term from the pattern
                # (reverse the escaping to get readable term)
                term = pattern.pattern.replace(r'\b', '').replace('\\', '')
                matched_terms.add(term.lower())
        
        if total_count > 0:
            results[keyword_id] = (total_count, matched_terms)
    
    return results


# --------------------------------------------------
# Signal Computation
# --------------------------------------------------

def build_event_keyword_map(
    novel_name: str,
    run_id: str,
    dictionary: dict = KEYWORD_DICTIONARY,
    source_dir: Optional[str] = None,
) -> EventKeywordSurfaceMap:
    """
    Build the event keyword surface map from chapter files.
    
    This can operate on either CONDENSED CHAPTERS or RAW CHAPTERS,
    controlled by the source_dir parameter.
    
    Process:
    1. Load all chapter texts
    2. Match keywords in each chapter
    3. Aggregate statistics across chapters
    4. Compute derived metrics
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        dictionary: Keyword dictionary to use
        source_dir: Base directory containing chapter files. Defaults to
                    CHAPTERS_CONDENSED_DIR. For raw chapters, pass RAW_CHAPTERS_DIR.
        
    Returns:
        EventKeywordSurfaceMap with all computed signals
    """
    # Default to condensed chapters for backward compatibility
    if source_dir is None:
        source_dir = CHAPTERS_CONDENSED_DIR
    
    chapters_dir = os.path.join(source_dir, novel_name)
    
    if not os.path.isdir(chapters_dir):
        raise FileNotFoundError(f"Chapters directory not found: {chapters_dir}")
    
    # Get sorted list of chapter files
    # Support both .condensed.txt (condensed) and .txt (raw) extensions
    chapter_files = sorted([
        f for f in os.listdir(chapters_dir)
        if f.endswith(".condensed.txt") or (f.endswith(".txt") and not f.endswith(".condensed.txt"))
    ])
    
    # Prefer .condensed.txt if both exist (shouldn't happen, but be safe)
    condensed_files = [f for f in chapter_files if f.endswith(".condensed.txt")]
    raw_files = [f for f in chapter_files if f.endswith(".txt") and not f.endswith(".condensed.txt")]
    
    if condensed_files:
        chapter_files = condensed_files
    elif raw_files:
        chapter_files = raw_files
    else:
        raise FileNotFoundError(f"No chapter files found in: {chapters_dir}")
    
    total_chapters = len(chapter_files)
    
    # Compile keyword patterns once
    patterns = _compile_keyword_patterns(dictionary)
    
    # Initialize keyword signals
    keyword_signals: dict[str, KeywordSignal] = {}
    for keyword_id, (_, category) in patterns.items():
        keyword_signals[keyword_id] = KeywordSignal(
            keyword_id=keyword_id,
            category=category,
        )
    
    # Process each chapter
    for chapter_idx, chapter_file in enumerate(chapter_files):
        chapter_path = os.path.join(chapters_dir, chapter_file)
        
        with open(chapter_path, 'r', encoding='utf-8') as f:
            chapter_text = f.read()
        
        # Match keywords in this chapter
        matches = _match_keywords_in_text(chapter_text, patterns)
        
        # Update signals for each matched keyword
        for keyword_id, (count, matched_terms) in matches.items():
            signal = keyword_signals[keyword_id]
            
            # Update counts
            signal.mentions += count
            signal.mentions_per_chapter[chapter_idx] = count
            signal.chapters_present.append(chapter_idx)
            
            # Update matched terms
            for term in matched_terms:
                if term not in signal.matched_terms:
                    signal.matched_terms.append(term)
            
            # Update first/last seen
            if signal.first_seen_unit == -1:
                signal.first_seen_unit = chapter_idx
            signal.last_seen_unit = chapter_idx
    
    # Compute derived metrics
    for signal in keyword_signals.values():
        if signal.mentions > 0:
            # Narrative spread
            signal.narrative_spread = signal.last_seen_unit - signal.first_seen_unit + 1
            # Density
            signal.density = round(signal.mentions / total_chapters, 4)
            # Sort matched terms for determinism
            signal.matched_terms.sort()
    
    # Build category summary
    categories_found: dict[str, list[str]] = defaultdict(list)
    keywords_found = 0
    total_mentions = 0
    
    for keyword_id, signal in keyword_signals.items():
        if signal.mentions > 0:
            keywords_found += 1
            total_mentions += signal.mentions
            categories_found[signal.category].append(keyword_id)
    
    # Sort category lists for determinism
    for category in categories_found:
        categories_found[category].sort()
    
    # Build final map
    surface_map = EventKeywordSurfaceMap(
        novel_name=novel_name,
        run_id=run_id,
        total_chapters=total_chapters,
        total_keywords_searched=len(dictionary),
        total_keywords_found=keywords_found,
        total_mentions=total_mentions,
        keywords={k: v for k, v in keyword_signals.items() if v.mentions > 0},
        categories_found=dict(categories_found),
    )
    
    return surface_map


# --------------------------------------------------
# Persistence
# --------------------------------------------------

def save_event_keyword_map(
    surface_map: EventKeywordSurfaceMap,
    novel_name: str,
    run_id: str,
) -> str:
    """
    Save the event keyword surface map as a JSON artifact.
    
    Path: data/event_keywords/{novel_name}/{run_id}.event_keywords.json
    """
    output_dir = os.path.join(EVENT_KEYWORDS_DIR, novel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{run_id}.event_keywords.json")
    
    # Convert to dict
    map_dict = asdict(surface_map)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(map_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
    
    return output_file


# --------------------------------------------------
# Pipeline Integration
# --------------------------------------------------

def generate_event_keyword_map(
    novel_name: str,
    run_id: str,
    source_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Generate and save the event keyword surface map.
    
    This is the main entry point for pipeline integration.
    NON-BLOCKING: failures are logged but do not halt the pipeline.
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        source_dir: Base directory containing chapter files. Defaults to
                    CHAPTERS_CONDENSED_DIR. For raw chapters, pass RAW_CHAPTERS_DIR.
        
    Returns:
        Path to saved artifact, or None if generation failed
    """
    try:
        source_label = "raw" if source_dir == RAW_CHAPTERS_DIR else "condensed"
        print(f"\n[Event Keywords] Scanning {source_label} chapters for event keyword signals...")
        print(f"[Event Keywords] Dictionary version: {KEYWORD_DICTIONARY_VERSION}")
        print(f"[Event Keywords] Keywords in dictionary: {len(KEYWORD_DICTIONARY)}")
        
        # Build the map
        surface_map = build_event_keyword_map(
            novel_name=novel_name,
            run_id=run_id,
            source_dir=source_dir,
        )
        
        # Save artifact
        output_path = save_event_keyword_map(surface_map, novel_name, run_id)
        
        print(f"[Event Keywords] Scanned {surface_map.total_chapters} chapters")
        print(f"[Event Keywords] Found {surface_map.total_keywords_found}/{surface_map.total_keywords_searched} "
              f"keywords ({surface_map.total_mentions} total mentions)")
        print(f"[Event Keywords] Saved to: {output_path}")
        
        # Print top keywords by mentions
        if surface_map.keywords:
            print("[Event Keywords] Top 5 keywords by mention count:")
            sorted_keywords = sorted(
                surface_map.keywords.values(),
                key=lambda k: (-k.mentions, k.keyword_id)
            )
            for signal in sorted_keywords[:5]:
                print(f"  - {signal.keyword_id}: {signal.mentions} mentions "
                      f"(spread={signal.narrative_spread}, density={signal.density:.2f})")
        
        # Print categories found
        if surface_map.categories_found:
            print(f"[Event Keywords] Categories with signals: {list(surface_map.categories_found.keys())}")
        
        return output_path
        
    except Exception as e:
        print(f"[Event Keywords] ⚠️ Failed to generate event keyword map: {e}")
        return None


# --------------------------------------------------
# Dictionary Management Utilities
# --------------------------------------------------

def get_dictionary_info() -> dict:
    """
    Get information about the current keyword dictionary.
    
    Useful for documentation and debugging.
    """
    categories = defaultdict(list)
    for keyword_id, config in KEYWORD_DICTIONARY.items():
        category = config.get("category", "uncategorized")
        categories[category].append(keyword_id)
    
    total_terms = sum(
        len(config.get("terms", []))
        for config in KEYWORD_DICTIONARY.values()
    )
    
    return {
        "version": KEYWORD_DICTIONARY_VERSION,
        "total_keywords": len(KEYWORD_DICTIONARY),
        "total_terms": total_terms,
        "categories": dict(categories),
    }


def list_keywords_by_category(category: str) -> list[tuple[str, list[str]]]:
    """
    List all keywords in a specific category.
    
    Returns list of (keyword_id, terms) tuples.
    """
    result = []
    for keyword_id, config in KEYWORD_DICTIONARY.items():
        if config.get("category") == category:
            result.append((keyword_id, config.get("terms", [])))
    return sorted(result)


# --------------------------------------------------
# Standalone Execution
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python event_keywords.py <novel_name> [run_id]")
        print("\nScans condensed novel for event-related keyword signals.")
        print("\nExample:")
        print('  python event_keywords.py "Heaven Reincarnation"')
        print('  python event_keywords.py "Heaven Reincarnation" "my_run_id"')
        print("\nDictionary Info:")
        info = get_dictionary_info()
        print(f"  Version: {info['version']}")
        print(f"  Keywords: {info['total_keywords']}")
        print(f"  Terms: {info['total_terms']}")
        print(f"  Categories: {list(info['categories'].keys())}")
        print("\nThis extracts LEXICAL SIGNALS, not event confirmations.")
        sys.exit(1)
    
    novel_name = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else "standalone_keywords"
    
    output_path = generate_event_keyword_map(novel_name, run_id)
    
    if output_path:
        print(f"\n✓ Event keyword map generated: {output_path}")
    else:
        print("\n✗ Event keyword map generation failed")
        sys.exit(1)
