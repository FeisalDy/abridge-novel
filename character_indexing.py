"""
Character Surface Indexing for Abridge Pipeline

PURPOSE (TIER-2 STRUCTURAL FEATURE):
This module extracts SURFACE-LEVEL CHARACTER NAME STATISTICS from the
final condensed novel text. It provides factual data to enable later
Tier-3 features (e.g., genre/tag detection) without performing any
narrative interpretation itself.

============================================================
WHAT THIS IS
============================================================

This is a STRUCTURAL, OBSERVATIONAL feature that:
- Extracts proper names/named entities as VERBATIM STRINGS
- Produces purely STATISTICAL, surface-level data
- Outputs a machine-readable JSON artifact
- Is DETERMINISTIC (same input always produces same output)

============================================================
WHAT THIS IS NOT (CRITICAL)
============================================================

This feature DOES NOT:
- Identify protagonists or antagonists
- Resolve aliases ("Li Qiye" vs "Young Master" as same person)
- Merge name variants ("Yu Canghai" vs "Canghai")
- Infer character identities or relationships
- Assign importance, roles, or narrative significance
- Perform coreference resolution
- Interpret pronouns
- Rank characters by story importance
- Filter names based on heuristics

Each distinct string is treated as a DISTINCT ENTRY.
This is NOT character analysis. This is NOT narrative understanding.

============================================================
OUTPUT CONTRACT
============================================================

The index contains, for each detected name:
- name: verbatim string as it appears in text
- mentions: total occurrence count
- first_seen: chapter identifier of first appearance
- chapters_present: list of chapters where name appears

Optional (if co-occurrence is enabled):
- co_occurrences: dict mapping other names to co-occurrence counts
  (purely statistical, window-based, no semantic meaning)

============================================================
CONSUMER WARNING
============================================================

Downstream consumers MUST understand:
- Names are RAW STRINGS, not resolved identities
- Statistics are SURFACE-LEVEL, not narrative importance
- Co-occurrences are PROXIMITY-BASED, not relationship indicators
- This data requires further processing for any semantic use

============================================================
IMPLEMENTATION NOTES
============================================================

Name extraction uses a conservative heuristic:
- Capitalized word sequences (2+ consecutive capitalized words)
- Single capitalized words that appear multiple times
- Excludes common sentence starters and articles

This is intentionally CONSERVATIVE to minimize false positives.
False negatives (missed names) are acceptable; false positives
(non-names marked as names) would pollute downstream analysis.
"""

import os
import re
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Output directory for character indices
CHARACTER_INDEX_DIR = os.getenv("ABRIDGE_CHARACTER_INDEX_DIR", "data/character_index")

# Novel condensation directory (must match run_pipeline.py)
NOVEL_CONDENSED_DIR = "data/novel_condensed"

# Chapters condensation directory (for per-chapter indexing)
CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"

# Raw chapters directory (for analysis-first pipeline)
RAW_CHAPTERS_DIR = "data/raw"

# Minimum mentions for a single-word name to be included
# (Multi-word names like "Li Qiye" are always included)
MIN_SINGLE_WORD_MENTIONS = 2

# Co-occurrence window size (sentences)
# Two names appearing within this many sentences are considered co-occurring
CO_OCCURRENCE_WINDOW = 3

# Common words to exclude from single-word name detection
# These are frequently capitalized but rarely character names
EXCLUDED_WORDS = frozenset({
    # Sentence starters / common words often capitalized
    "The", "A", "An", "This", "That", "These", "Those",
    "He", "She", "It", "They", "We", "I", "You",
    "His", "Her", "Its", "Their", "Our", "My", "Your",
    "What", "When", "Where", "Why", "How", "Who", "Which",
    "If", "Then", "But", "And", "Or", "So", "Yet", "For",
    "After", "Before", "During", "While", "As", "Since",
    "However", "Therefore", "Thus", "Hence", "Meanwhile",
    "Chapter", "Part", "Section", "Book", "Volume", "Arc",
    # Common titles (we want "Yu Canghai" not just "Master")
    "Master", "Lord", "Lady", "Sir", "Madam", "Elder", "Senior",
    "Junior", "Young", "Old", "Grand", "Great", "Divine",
    # Directions and locations often capitalized
    "North", "South", "East", "West", "Central",
    "Mountain", "River", "Valley", "Palace", "Hall", "Sect",
    # Time references
    "Today", "Tomorrow", "Yesterday", "Now", "Later",
    # Additional common sentence starters / prepositions
    "In", "On", "At", "By", "To", "From", "With", "Within",
    "Through", "Into", "Upon", "Across", "Along", "Among",
    "Between", "Beyond", "Over", "Under", "Above", "Below",
    "Here", "There", "Once", "Eventually", "Finally", "Suddenly",
    "Each", "Every", "Both", "All", "Some", "Many", "Few",
    "First", "Second", "Third", "Next", "Last", "Final",
    # Common adjectives that may be capitalized
    "Good", "Evil", "True", "False", "Real", "Pure", "Dark", "Light",
    "Strong", "Weak", "High", "Low", "Deep", "Wide", "Long", "Short",
    # Miscellaneous
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Hundred", "Thousand", "Million",
    "Still", "Just", "Only", "Even", "Also", "Already", "Although", "Accidental",
    "Amidst", "Analyst", "Amid", "Awkward", "Being", "Because", "Everyone", "Experiments",

})


# --------------------------------------------------
# Data structures
# --------------------------------------------------

@dataclass
class CharacterEntry:
    """
    Surface-level data for a single detected name.
    
    WARNING: This is NOT a character identity.
    Each distinct string is a separate entry.
    "Li Qiye" and "Young Master Li" are DIFFERENT entries
    even if they refer to the same narrative character.
    """
    name: str
    mentions: int
    first_seen: str  # Chapter identifier
    chapters_present: list[str] = field(default_factory=list)


@dataclass 
class CharacterIndex:
    """
    Complete character surface index for a novel.
    
    This is a STRUCTURAL ARTIFACT containing raw statistics.
    It carries NO semantic or narrative meaning.
    """
    novel_name: str
    run_id: str
    extraction_method: str  # Document how names were extracted
    total_unique_names: int
    total_mentions: int
    characters: list[CharacterEntry] = field(default_factory=list)
    # Optional co-occurrence matrix (name -> name -> count)
    # Symmetric: co_occurrences["A"]["B"] == co_occurrences["B"]["A"]
    co_occurrences: Optional[dict[str, dict[str, int]]] = None
    
    # Metadata for downstream consumers
    warnings: list[str] = field(default_factory=lambda: [
        "Names are raw strings, not resolved identities",
        "Statistics are surface-level counts, not narrative importance",
        "Co-occurrences indicate proximity, not relationships",
    ])


# --------------------------------------------------
# Name extraction (conservative heuristic)
# --------------------------------------------------

def _extract_potential_names(text: str) -> list[str]:
    """
    Extract potential character names from text using conservative heuristics.
    
    Strategy:
    1. Find capitalized word sequences (likely proper names)
    2. Filter out common non-name capitalized words
    3. Return all matches as-is (no normalization)
    
    This is intentionally CONSERVATIVE:
    - Prefers false negatives over false positives
    - Multi-word names (e.g., "Li Qiye") are prioritized
    - Single-word names require frequency threshold
    
    Returns:
        List of potential name strings (may contain duplicates)
    """
    # Pattern: One or more capitalized words in sequence
    # Matches: "Li Qiye", "Yu Canghai", "Zhao Gao"
    # Also matches single capitalized words
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    
    matches = re.findall(pattern, text)
    return matches


def _filter_names(
    name_counts: Counter,
    min_single_word: int = MIN_SINGLE_WORD_MENTIONS,
) -> dict[str, int]:
    """
    Filter potential names to reduce false positives.
    
    Rules:
    1. Multi-word names (e.g., "Li Qiye") are always kept
    2. Single-word names must appear >= min_single_word times
    3. Excluded common words are removed
    
    Args:
        name_counts: Counter of potential name -> occurrence count
        min_single_word: Minimum mentions for single-word names
        
    Returns:
        Filtered dict of name -> count
    """
    filtered = {}

    for name, count in name_counts.items():
        tokens = name.split()

        # Reject names starting with excluded words
        if _contains_excluded_token(tokens):
            continue

        # Multi-word names (after leading-token check)
        if len(tokens) > 1:
            filtered[name] = count

        # Single-word names need minimum frequency
        elif (
                len(tokens) == 1
                and count >= min_single_word
                and len(tokens[0]) >= 4
        ):
            filtered[name] = count

        # Reject weird casing artifacts
        if not all(tok[0].isupper() and tok[1:].islower() for tok in tokens):
            continue
    
    return filtered

def _normalize_text(text: str) -> str:
    # Collapse all whitespace (including newlines) into single spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _contains_excluded_token(tokens: list[str]) -> bool:
    return any(tok in EXCLUDED_WORDS for tok in tokens)

# --------------------------------------------------
# Chapter-level indexing
# --------------------------------------------------

def _index_chapter(
    chapter_text: str,
    chapter_id: str,
) -> tuple[dict[str, int], list[str]]:
    """
    Index names in a single chapter.
    
    Args:
        chapter_text: Raw text of the chapter
        chapter_id: Identifier for the chapter (e.g., "chapter_001")
        
    Returns:
        (name_counts, sentence_list) tuple
        - name_counts: dict of name -> occurrence count in this chapter
        - sentence_list: list of sentences for co-occurrence calculation
    """
    # Extract potential names
    chapter_text = _normalize_text(chapter_text)
    potential_names = _extract_potential_names(chapter_text)
    name_counts = Counter(potential_names)
    
    # Split into sentences for co-occurrence
    # Simple sentence splitting (period, exclamation, question mark)
    sentences = re.split(r'[.!?]+', chapter_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return dict(name_counts), sentences


# --------------------------------------------------
# Co-occurrence calculation
# --------------------------------------------------

def _calculate_co_occurrences(
    chapters_data: list[tuple[str, dict[str, int], list[str]]],
    filtered_names: set[str],
    window_size: int = CO_OCCURRENCE_WINDOW,
) -> dict[str, dict[str, int]]:
    """
    Calculate sentence-window co-occurrences between names.
    
    Two names co-occur if they appear within `window_size` sentences
    of each other. This is purely POSITIONAL - no semantic meaning.
    
    The result is SYMMETRIC: co_occur["A"]["B"] == co_occur["B"]["A"]
    
    Args:
        chapters_data: List of (chapter_id, name_counts, sentences) tuples
        filtered_names: Set of names to track co-occurrences for
        window_size: Number of sentences defining the co-occurrence window
        
    Returns:
        Dict mapping name -> name -> co-occurrence count
    """
    co_occur = defaultdict(lambda: defaultdict(int))
    
    for chapter_id, _, sentences in chapters_data:
        # Extract names present in each sentence
        sentence_names = []
        for sentence in sentences:
            names_in_sentence = set()
            for name in filtered_names:
                if name in sentence:
                    names_in_sentence.add(name)
            sentence_names.append(names_in_sentence)
        
        # Count co-occurrences within window
        for i, names_i in enumerate(sentence_names):
            # Look at sentences within window
            window_end = min(i + window_size + 1, len(sentence_names))
            for j in range(i, window_end):
                names_j = sentence_names[j]
                # All pairs of names across these sentences co-occur
                for name_a in names_i:
                    for name_b in names_j:
                        if name_a != name_b:
                            co_occur[name_a][name_b] += 1
    
    # Convert to regular dict and ensure symmetry
    result = {}
    for name_a in co_occur:
        result[name_a] = dict(co_occur[name_a])
    
    return result


# --------------------------------------------------
# Main indexing function
# --------------------------------------------------

def build_character_index(
    novel_name: str,
    run_id: str,
    include_co_occurrences: bool = True,
    source_dir: Optional[str] = None,
) -> CharacterIndex:
    """
    Build the character surface index from chapter files.
    
    This can operate on either CONDENSED CHAPTERS or RAW CHAPTERS,
    controlled by the source_dir parameter. This preserves chapter
    boundaries for accurate first_seen and chapters_present data.
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        include_co_occurrences: Whether to calculate co-occurrence matrix
        source_dir: Base directory containing chapter files. Defaults to
                    CHAPTERS_CONDENSED_DIR. For raw chapters, pass RAW_CHAPTERS_DIR.
        
    Returns:
        CharacterIndex containing all extracted data
        
    Raises:
        FileNotFoundError: If chapters directory doesn't exist
    """
    # Default to condensed chapters for backward compatibility
    if source_dir is None:
        source_dir = CHAPTERS_CONDENSED_DIR
    
    chapters_dir = os.path.join(source_dir, novel_name)
    
    if not os.path.isdir(chapters_dir):
        raise FileNotFoundError(
            f"Chapters directory not found: {chapters_dir}"
        )
    
    # Collect all chapter files in sorted order (deterministic)
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
        file_suffix = ".condensed.txt"
    elif raw_files:
        chapter_files = raw_files
        file_suffix = ".txt"
    else:
        raise FileNotFoundError(
            f"No chapter files found in: {chapters_dir}"
        )
    
    # Process each chapter
    chapters_data = []  # (chapter_id, name_counts, sentences)
    global_counts = Counter()
    name_to_chapters = defaultdict(list)
    name_to_first_seen = {}
    
    for chapter_file in chapter_files:
        # Extract chapter ID from filename 
        # e.g., "chapter_001.condensed.txt" -> "chapter_001"
        # e.g., "chapter_001.txt" -> "chapter_001"
        chapter_id = chapter_file.replace(file_suffix, "")
        
        # Read chapter text
        chapter_path = os.path.join(chapters_dir, chapter_file)
        with open(chapter_path, 'r', encoding='utf-8') as f:
            chapter_text = f.read()
        
        # Index this chapter
        name_counts, sentences = _index_chapter(chapter_text, chapter_id)
        chapters_data.append((chapter_id, name_counts, sentences))
        
        # Accumulate global statistics
        for name, count in name_counts.items():
            global_counts[name] += count
            name_to_chapters[name].append(chapter_id)
            if name not in name_to_first_seen:
                name_to_first_seen[name] = chapter_id
    
    # Filter names to reduce false positives
    filtered_counts = _filter_names(global_counts)
    filtered_names = set(filtered_counts.keys())
    
    # Build character entries (sorted by mention count, then name for determinism)
    characters = []
    for name in sorted(filtered_names, key=lambda n: (-filtered_counts[n], n)):
        entry = CharacterEntry(
            name=name,
            mentions=filtered_counts[name],
            first_seen=name_to_first_seen[name],
            chapters_present=name_to_chapters[name],
        )
        characters.append(entry)
    
    # Calculate co-occurrences if requested
    co_occurrences = None
    if include_co_occurrences and filtered_names:
        co_occurrences = _calculate_co_occurrences(
            chapters_data, filtered_names
        )
        # Only include names that have co-occurrences
        co_occurrences = {
            k: v for k, v in co_occurrences.items() if v
        }
        if not co_occurrences:
            co_occurrences = None
    
    # Build final index
    index = CharacterIndex(
        novel_name=novel_name,
        run_id=run_id,
        extraction_method=(
            "Conservative heuristic: capitalized word sequences, "
            f"single-word names require >= {MIN_SINGLE_WORD_MENTIONS} mentions, "
            f"excluded common words ({len(EXCLUDED_WORDS)} patterns)"
        ),
        total_unique_names=len(characters),
        total_mentions=sum(filtered_counts.values()),
        characters=characters,
        co_occurrences=co_occurrences,
    )
    
    return index


# --------------------------------------------------
# Persistence
# --------------------------------------------------

def save_character_index(
    index: CharacterIndex,
    novel_name: str,
    run_id: str,
) -> str:
    """
    Save the character index as a JSON artifact.
    
    The index is stored in a run-specific location to prevent overwrites.
    Path: data/character_index/{novel_name}/{run_id}.character_index.json
    
    Args:
        index: The CharacterIndex to save
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        
    Returns:
        Path to the saved artifact
    """
    # Create output directory
    output_dir = os.path.join(CHARACTER_INDEX_DIR, novel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # Build output path (run-specific to prevent overwrites)
    output_file = os.path.join(output_dir, f"{run_id}.character_index.json")
    
    # Convert to dict for JSON serialization
    index_dict = asdict(index)
    
    # Write with stable formatting (sorted keys, indent for readability)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
    
    return output_file


# --------------------------------------------------
# Pipeline integration
# --------------------------------------------------

def generate_character_index(
    novel_name: str,
    run_id: str,
    include_co_occurrences: bool = True,
    source_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Generate and save the character surface index.
    
    This is the main entry point for pipeline integration.
    It is NON-BLOCKING: failures are logged but do not halt the pipeline.
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        include_co_occurrences: Whether to calculate co-occurrence matrix
        source_dir: Base directory containing chapter files. Defaults to
                    CHAPTERS_CONDENSED_DIR. For raw chapters, pass RAW_CHAPTERS_DIR.
        
    Returns:
        Path to the saved artifact, or None if generation failed
    """
    try:
        source_label = "raw" if source_dir == RAW_CHAPTERS_DIR else "condensed"
        print(f"\n[Character Index] Generating character surface index from {source_label} chapters...")
        
        # Build the index
        index = build_character_index(
            novel_name=novel_name,
            run_id=run_id,
            include_co_occurrences=include_co_occurrences,
            source_dir=source_dir,
        )
        
        # Save the artifact
        output_path = save_character_index(index, novel_name, run_id)
        
        print(f"[Character Index] Found {index.total_unique_names} unique names "
              f"({index.total_mentions} total mentions)")
        print(f"[Character Index] Saved to: {output_path}")
        
        # Print top names for quick inspection
        if index.characters:
            print("[Character Index] Top 5 names by mention count:")
            for entry in index.characters[:5]:
                print(f"  - {entry.name}: {entry.mentions} mentions "
                      f"(first in {entry.first_seen})")
        
        return output_path
        
    except Exception as e:
        # NON-BLOCKING: Log error but don't halt pipeline
        print(f"[Character Index] ⚠️ Failed to generate index: {e}")
        return None


# --------------------------------------------------
# Standalone execution (for testing/debugging)
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python character_indexing.py <novel_name> [run_id]")
        print("\nExample:")
        print('  python character_indexing.py "Heaven Reincarnation"')
        print('  python character_indexing.py "Heaven Reincarnation" "test_run_001"')
        sys.exit(1)
    
    novel_name = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else "standalone_test"
    
    output_path = generate_character_index(novel_name, run_id)
    
    if output_path:
        print(f"\n✓ Character index generated: {output_path}")
    else:
        print("\n✗ Character index generation failed")
        sys.exit(1)
