"""
Character Salience Index for Abridge Pipeline (Tier-3.1)

PURPOSE:
This module computes CHARACTER SALIENCE SCORES from Tier-2 Character Surface
Index data. It measures TEXTUAL DOMINANCE — how much a character name dominates
the narrative surface — NOT narrative importance, role, or quality.

============================================================
WHAT THIS IS
============================================================

This is a DERIVED, OBSERVATIONAL feature that:
- Consumes ONLY Tier-2 Character Surface Index data (immutable input)
- Computes a deterministic salience score per character
- Produces a ranked list normalized to 0.0–1.0
- Stores results as a read-only Tier-3 artifact

============================================================
WHAT THIS IS NOT (CRITICAL)
============================================================

This feature DOES NOT:
- Identify protagonists or antagonists
- Infer narrative importance or story role
- Detect relationships or character dynamics
- Interpret story meaning or quality
- Modify any upstream artifacts (Tier-2 or condensation)

Salience measures SURFACE DOMINANCE, not STORY SIGNIFICANCE.
A character with high salience may be a narrator, a background element,
or even a location that happens to have a proper name.

============================================================
SALIENCE FORMULA (DOCUMENTED)
============================================================

Salience is computed as a weighted combination of three dimensions:

1. MENTION FREQUENCY (weight: 0.5)
   - Normalized count of name appearances
   - Higher mentions = higher frequency score
   - Formula: mentions / max_mentions_in_novel

2. CHAPTER COVERAGE (weight: 0.3)
   - Proportion of chapters where the name appears
   - Measures narrative spread
   - Formula: chapters_present / total_chapters

3. PERSISTENCE (weight: 0.2)
   - Measures early-to-late presence vs. clustered mentions
   - Characters appearing from start to end score higher
   - Formula: span_ratio * coverage_density
     - span_ratio = (last_chapter - first_chapter + 1) / total_chapters
     - coverage_density = chapters_present / span

All weights are configurable constants, not learned parameters.
Final salience is normalized to [0.0, 1.0] relative to max in the run.

============================================================
CONSUMER WARNING
============================================================

Downstream consumers MUST understand:
- Salience is a SURFACE METRIC, not a narrative judgment
- High salience does NOT mean "main character"
- Low salience does NOT mean "unimportant"
- Scores are relative within a single novel/run
- This data enables analysis; it does not perform it

============================================================
STORAGE
============================================================

Salience data is stored per run_id in:
- JSON artifact: data/character_salience/{novel_name}/{run_id}.character_salience.json

This artifact is marked as Tier-3 (derived) and never overwrites previous runs.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# --------------------------------------------------
# Configuration: Salience Weights
# --------------------------------------------------
# These weights determine how each dimension contributes to final salience.
# They are DETERMINISTIC CONSTANTS, not learned parameters.
# Adjust these to change salience behavior (document any changes).

# MENTION_WEIGHT: How much raw frequency matters (0.0-1.0)
# Higher = more weight on characters mentioned often
MENTION_WEIGHT = 0.4

# COVERAGE_WEIGHT: How much narrative spread matters (0.0-1.0)
# Higher = more weight on characters appearing across many chapters
COVERAGE_WEIGHT = 0.2

# PERSISTENCE_WEIGHT: How much early-to-late presence matters (0.0-1.0)
# Higher = more weight on characters with sustained presence
PERSISTENCE_WEIGHT = 0.2

# EVENT_PARTICIPATION_WEIGHT: How much actor-event linkage matters (0.0-1.0)
# Higher = more weight on characters co-occurring with event keywords
# This distinguishes characters who ACT from those who merely APPEAR
EVENT_PARTICIPATION_WEIGHT = 0.2

# Saturation constant for event participation normalization
# Characters linked to this many unique event types get max score (1.0)
EVENT_PARTICIPATION_SATURATION = 10

# Sanity check: weights should sum to 1.0
assert abs(MENTION_WEIGHT + COVERAGE_WEIGHT + PERSISTENCE_WEIGHT + EVENT_PARTICIPATION_WEIGHT - 1.0) < 0.001, \
    "Salience weights must sum to 1.0"


# --------------------------------------------------
# Configuration: Paths
# --------------------------------------------------

# Output directory for salience indices
CHARACTER_SALIENCE_DIR = os.getenv(
    "ABRIDGE_CHARACTER_SALIENCE_DIR",
    "data/character_salience"
)

# Input directory for Tier-2 character indices
CHARACTER_INDEX_DIR = os.getenv(
    "ABRIDGE_CHARACTER_INDEX_DIR",
    "data/character_index"
)


# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class CharacterSalienceEntry:
    """
    Salience data for a single character name.
    
    WARNING: This measures TEXTUAL DOMINANCE, not narrative importance.
    A high salience score does NOT mean "main character".
    
    The salience_score is a weighted combination of four dimensions:
    - mention_score: Raw frequency of name appearances
    - coverage_score: Proportion of chapters where character appears
    - persistence_score: Sustained presence from early to late chapters
    - event_participation_score: Co-occurrence with event keywords
    
    Event participation distinguishes characters who ACT (appear near
    event keywords like "battle", "breakthrough", "betrayal") from
    characters who merely APPEAR in the text.
    """
    name: str
    
    # Raw metrics from Tier-2 (for auditability)
    mentions: int
    chapters_present: int
    first_seen_index: int  # 0-based chapter index
    last_seen_index: int   # 0-based chapter index
    
    # Computed dimension scores (each 0.0-1.0)
    mention_score: float             # Normalized frequency
    coverage_score: float            # Chapter spread
    persistence_score: float         # Early-to-late presence
    event_participation_score: float # Actor-event linkage
    
    # Final salience (weighted combination, 0.0-1.0)
    salience_score: float
    
    # Rank among all characters in this run (1 = highest salience)
    rank: int


@dataclass
class CharacterSalienceIndex:
    """
    Complete character salience index for a novel run.
    
    This is a TIER-3 DERIVED ARTIFACT.
    It measures textual dominance, NOT narrative importance.
    """
    # Identification
    novel_name: str
    run_id: str
    tier: str = "tier-3.1"
    
    # Source data reference
    source_tier2_run_id: str = ""
    
    # Novel metadata (for score computation)
    total_chapters: int = 0
    total_characters: int = 0
    total_mentions: int = 0
    
    # Weight configuration (for reproducibility)
    weights: dict = field(default_factory=lambda: {
        "mention": MENTION_WEIGHT,
        "coverage": COVERAGE_WEIGHT,
        "persistence": PERSISTENCE_WEIGHT,
        "event_participation": EVENT_PARTICIPATION_WEIGHT,
    })
    
    # Event participation metadata
    event_participation_enabled: bool = True
    event_participation_saturation: int = EVENT_PARTICIPATION_SATURATION
    
    # Salience entries (sorted by rank)
    characters: list[CharacterSalienceEntry] = field(default_factory=list)
    
    # Warnings for downstream consumers
    warnings: list[str] = field(default_factory=lambda: [
        "Salience measures TEXTUAL DOMINANCE, not narrative importance",
        "High salience does NOT mean 'main character' or 'protagonist'",
        "Scores are relative within this novel/run only",
        "This is a measurement layer, not a literary judgment",
    ])


# --------------------------------------------------
# Core Computation
# --------------------------------------------------

def _parse_chapter_index(chapter_id: str) -> int:
    """
    Extract numeric index from chapter identifier.
    
    Handles formats like:
    - "chapter_001" -> 0
    - "chapter_42" -> 41
    - "arc_01" -> 0
    
    Falls back to 0 if parsing fails (documented, not silent).
    """
    import re
    match = re.search(r'(\d+)', chapter_id)
    if match:
        return int(match.group(1)) - 1  # Convert to 0-based
    return 0


def _compute_mention_score(mentions: int, max_mentions: int) -> float:
    """
    Compute normalized mention frequency score.
    
    Formula: mentions / max_mentions
    
    Args:
        mentions: Number of times this character is mentioned
        max_mentions: Maximum mentions of any character in the novel
        
    Returns:
        Score in [0.0, 1.0]
    """
    if max_mentions == 0:
        return 0.0
    return mentions / max_mentions


def _compute_coverage_score(chapters_present: int, total_chapters: int) -> float:
    """
    Compute chapter coverage score.
    
    Formula: chapters_present / total_chapters
    
    A character appearing in all chapters gets 1.0.
    A character appearing in one chapter gets 1/total_chapters.
    
    Args:
        chapters_present: Number of chapters where character appears
        total_chapters: Total chapters in the novel
        
    Returns:
        Score in [0.0, 1.0]
    """
    if total_chapters == 0:
        return 0.0
    return chapters_present / total_chapters


def _compute_persistence_score(
    first_seen_index: int,
    last_seen_index: int,
    chapters_present: int,
    total_chapters: int,
) -> float:
    """
    Compute persistence score measuring sustained presence.
    
    This captures whether a character appears throughout the narrative
    vs. being clustered in a specific section.
    
    Formula: span_ratio * coverage_density
    - span_ratio: (last - first + 1) / total_chapters
      How much of the narrative timeline the character spans
    - coverage_density: chapters_present / span
      How consistently the character appears within their span
    
    A character appearing in chapters 1, 5, and 10 of a 10-chapter novel:
    - span_ratio = (10 - 1 + 1) / 10 = 1.0 (spans entire novel)
    - span = 10
    - coverage_density = 3 / 10 = 0.3 (appears in 30% of their span)
    - persistence = 1.0 * 0.3 = 0.3
    
    Args:
        first_seen_index: 0-based index of first appearance
        last_seen_index: 0-based index of last appearance
        chapters_present: Number of chapters where character appears
        total_chapters: Total chapters in the novel
        
    Returns:
        Score in [0.0, 1.0]
    """
    if total_chapters == 0 or chapters_present == 0:
        return 0.0
    
    # Calculate span (number of chapters from first to last appearance)
    span = last_seen_index - first_seen_index + 1
    
    # Span ratio: how much of the novel timeline they span
    span_ratio = span / total_chapters
    
    # Coverage density: how consistently they appear within their span
    coverage_density = chapters_present / span if span > 0 else 0.0
    
    return span_ratio * coverage_density


def _compute_event_participation_score(
    event_links: dict,
    saturation: int = EVENT_PARTICIPATION_SATURATION,
) -> float:
    """
    Compute event participation score from character-event links.
    
    This measures how many UNIQUE event types (keyword_ids) a character
    co-occurs with. Characters linked to diverse event types are considered
    more "active" in the narrative surface.
    
    Formula: min(unique_event_count / saturation, 1.0)
    
    The saturation constant caps the score at 1.0 to prevent characters
    with extreme event diversity from dominating.
    
    WARNING: This is LEXICAL CO-OCCURRENCE, not confirmed event participation.
    A character appearing near "death" does not mean they died or killed.
    
    Args:
        event_links: Dict mapping keyword_id -> count (from Tier-2 event_links)
        saturation: Number of unique events for max score (default: 10)
        
    Returns:
        Score in [0.0, 1.0]
    """
    if not event_links or saturation <= 0:
        return 0.0
    
    # Count unique event types (keyword_ids)
    unique_event_count = len(event_links)
    
    # Normalize and clamp to [0.0, 1.0]
    score = unique_event_count / saturation
    return min(score, 1.0)


def _compute_salience_score(
    mention_score: float,
    coverage_score: float,
    persistence_score: float,
    event_participation_score: float,
) -> float:
    """
    Compute weighted salience score from dimension scores.
    
    Formula: (mention_score * MENTION_WEIGHT) +
             (coverage_score * COVERAGE_WEIGHT) +
             (persistence_score * PERSISTENCE_WEIGHT) +
             (event_participation_score * EVENT_PARTICIPATION_WEIGHT)
    
    Args:
        mention_score: Normalized frequency score [0.0, 1.0]
        coverage_score: Chapter spread score [0.0, 1.0]
        persistence_score: Sustained presence score [0.0, 1.0]
        event_participation_score: Actor-event linkage score [0.0, 1.0]
        
    Returns:
        Weighted score (may exceed 1.0 before normalization)
    """
    return (
        mention_score * MENTION_WEIGHT +
        coverage_score * COVERAGE_WEIGHT +
        persistence_score * PERSISTENCE_WEIGHT +
        event_participation_score * EVENT_PARTICIPATION_WEIGHT
    )


# --------------------------------------------------
# Main Computation Function
# --------------------------------------------------

def build_salience_index(
    tier2_data: dict,
    novel_name: str,
    run_id: str,
    source_run_id: str,
) -> CharacterSalienceIndex:
    """
    Build character salience index from Tier-2 surface data.
    
    This is the main computation function. It:
    1. Extracts raw metrics from Tier-2 data
    2. Computes dimension scores for each character
    3. Computes weighted salience scores
    4. Normalizes to [0.0, 1.0] relative to max
    5. Ranks characters by salience
    
    Args:
        tier2_data: Parsed Tier-2 Character Surface Index JSON
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        source_run_id: Run ID of the source Tier-2 data
        
    Returns:
        CharacterSalienceIndex with all computed data
    """
    characters_data = tier2_data.get("characters", [])
    
    if not characters_data:
        # Handle empty input gracefully
        return CharacterSalienceIndex(
            novel_name=novel_name,
            run_id=run_id,
            source_tier2_run_id=source_run_id,
            total_chapters=0,
            total_characters=0,
            total_mentions=0,
        )
    
    # Determine total chapters from all character data
    all_chapters = set()
    for char in characters_data:
        all_chapters.update(char.get("chapters_present", []))
    total_chapters = len(all_chapters)
    
    # If we can't determine chapter count from data, fall back to max index
    if total_chapters == 0:
        max_index = 0
        for char in characters_data:
            for ch in char.get("chapters_present", []):
                idx = _parse_chapter_index(ch)
                max_index = max(max_index, idx)
        total_chapters = max_index + 1 if max_index > 0 else 1
    
    # Find max mentions for normalization
    max_mentions = max(char.get("mentions", 0) for char in characters_data)
    
    # Compute scores for each character
    entries = []
    for char in characters_data:
        name = char.get("name", "")
        mentions = char.get("mentions", 0)
        chapters_present_list = char.get("chapters_present", [])
        chapters_present = len(chapters_present_list)
        first_seen = char.get("first_seen", "")
        
        # Determine first and last chapter indices
        if chapters_present_list:
            chapter_indices = [_parse_chapter_index(ch) for ch in chapters_present_list]
            first_seen_index = min(chapter_indices)
            last_seen_index = max(chapter_indices)
        else:
            first_seen_index = _parse_chapter_index(first_seen)
            last_seen_index = first_seen_index
        
        # Compute dimension scores
        mention_score = _compute_mention_score(mentions, max_mentions)
        coverage_score = _compute_coverage_score(chapters_present, total_chapters)
        persistence_score = _compute_persistence_score(
            first_seen_index,
            last_seen_index,
            chapters_present,
            total_chapters,
        )
        
        # Extract event_links for this character from Tier-2 event_links data
        # The event_links in tier2_data maps character_name -> keyword_id -> count
        tier2_event_links = tier2_data.get("event_links", {}) or {}
        char_event_links = tier2_event_links.get(name, {})
        event_participation_score = _compute_event_participation_score(char_event_links)
        
        # Compute raw salience (before final normalization)
        raw_salience = _compute_salience_score(
            mention_score,
            coverage_score,
            persistence_score,
            event_participation_score,
        )
        
        entry = CharacterSalienceEntry(
            name=name,
            mentions=mentions,
            chapters_present=chapters_present,
            first_seen_index=first_seen_index,
            last_seen_index=last_seen_index,
            mention_score=round(mention_score, 4),
            coverage_score=round(coverage_score, 4),
            persistence_score=round(persistence_score, 4),
            event_participation_score=round(event_participation_score, 4),
            salience_score=raw_salience,  # Will normalize later
            rank=0,  # Will assign later
        )
        entries.append(entry)
    
    # Normalize salience scores to [0.0, 1.0]
    if entries:
        max_salience = max(e.salience_score for e in entries)
        if max_salience > 0:
            for entry in entries:
                entry.salience_score = round(entry.salience_score / max_salience, 4)
    
    # Sort by salience (descending) and assign ranks
    # Tie-breaker: alphabetical by name (for determinism)
    entries.sort(key=lambda e: (-e.salience_score, e.name))
    for i, entry in enumerate(entries):
        entry.rank = i + 1
    
    # Build final index
    total_mentions = sum(char.get("mentions", 0) for char in characters_data)
    
    return CharacterSalienceIndex(
        novel_name=novel_name,
        run_id=run_id,
        source_tier2_run_id=source_run_id,
        total_chapters=total_chapters,
        total_characters=len(entries),
        total_mentions=total_mentions,
        characters=entries,
    )


# --------------------------------------------------
# Tier-2 Data Loading
# --------------------------------------------------

def load_tier2_index(novel_name: str, run_id: str) -> Optional[tuple[dict, str]]:
    """
    Load Tier-2 Character Surface Index data.
    
    Searches for the index file in the expected location.
    If run_id is provided, looks for that specific run.
    Otherwise, finds the most recent index for the novel.
    
    Args:
        novel_name: Name of the novel
        run_id: Run ID to look for (or empty to find latest)
        
    Returns:
        (parsed_data, source_run_id) tuple, or None if not found
    """
    index_dir = os.path.join(CHARACTER_INDEX_DIR, novel_name)
    
    if not os.path.isdir(index_dir):
        return None
    
    # If specific run_id provided, look for that file
    if run_id:
        target_file = os.path.join(index_dir, f"{run_id}.character_index.json")
        if os.path.isfile(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                return json.load(f), run_id
    
    # Otherwise, find the most recent index file
    index_files = [
        f for f in os.listdir(index_dir)
        if f.endswith(".character_index.json")
    ]
    
    if not index_files:
        return None
    
    # Sort by modification time (most recent first)
    index_files.sort(
        key=lambda f: os.path.getmtime(os.path.join(index_dir, f)),
        reverse=True
    )
    
    latest_file = index_files[0]
    source_run_id = latest_file.replace(".character_index.json", "")
    
    with open(os.path.join(index_dir, latest_file), 'r', encoding='utf-8') as f:
        return json.load(f), source_run_id


# --------------------------------------------------
# Persistence
# --------------------------------------------------

def save_salience_index(
    index: CharacterSalienceIndex,
    novel_name: str,
    run_id: str,
) -> str:
    """
    Save the salience index as a JSON artifact.
    
    Path: data/character_salience/{novel_name}/{run_id}.character_salience.json
    
    Args:
        index: The CharacterSalienceIndex to save
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        
    Returns:
        Path to the saved artifact
    """
    output_dir = os.path.join(CHARACTER_SALIENCE_DIR, novel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{run_id}.character_salience.json")
    
    # Convert to dict for JSON serialization
    index_dict = asdict(index)
    
    # Write with stable formatting (sorted keys, indent for readability)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
    
    return output_file


# --------------------------------------------------
# Pipeline Integration
# --------------------------------------------------

def generate_salience_index(
    novel_name: str,
    run_id: str,
    tier2_run_id: str = "",
) -> Optional[str]:
    """
    Generate and save the character salience index.
    
    This is the main entry point for pipeline integration.
    It is NON-BLOCKING: failures are logged but do not halt the pipeline.
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        tier2_run_id: Specific Tier-2 run to use (or empty for latest)
        
    Returns:
        Path to the saved artifact, or None if generation failed
    """
    try:
        print("\n[Salience Index] Computing character salience scores...")
        
        # Load Tier-2 data
        tier2_result = load_tier2_index(novel_name, tier2_run_id)
        
        if tier2_result is None:
            print("[Salience Index] ⚠️ No Tier-2 character index found")
            print("[Salience Index] Run with --character-index first to generate Tier-2 data")
            return None
        
        tier2_data, source_run_id = tier2_result
        print(f"[Salience Index] Using Tier-2 data from run: {source_run_id}")
        
        # Build salience index
        index = build_salience_index(
            tier2_data=tier2_data,
            novel_name=novel_name,
            run_id=run_id,
            source_run_id=source_run_id,
        )
        
        # Save artifact
        output_path = save_salience_index(index, novel_name, run_id)
        
        print(f"[Salience Index] Computed salience for {index.total_characters} characters")
        print(f"[Salience Index] Saved to: {output_path}")
        
        # Print top characters for quick inspection
        if index.characters:
            print("[Salience Index] Top 5 characters by salience:")
            for entry in index.characters[:5]:
                print(f"  #{entry.rank} {entry.name}: "
                      f"salience={entry.salience_score:.3f} "
                      f"(mentions={entry.mentions}, "
                      f"coverage={entry.coverage_score:.2f}, "
                      f"persistence={entry.persistence_score:.2f}, "
                      f"events={entry.event_participation_score:.2f})")
        
        return output_path
        
    except Exception as e:
        # NON-BLOCKING: Log error but don't halt pipeline
        print(f"[Salience Index] ⚠️ Failed to generate salience index: {e}")
        return None


# --------------------------------------------------
# Standalone Execution
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python character_salience.py <novel_name> [run_id] [tier2_run_id]")
        print("\nComputes Character Salience Index (Tier-3.1) from Tier-2 data.")
        print("\nExample:")
        print('  python character_salience.py "Heaven Reincarnation"')
        print('  python character_salience.py "Heaven Reincarnation" "my_run_id"')
        print('  python character_salience.py "Heaven Reincarnation" "my_run_id" "tier2_run_id"')
        print("\nSalience Formula:")
        print(f"  salience = {MENTION_WEIGHT}*mention + {COVERAGE_WEIGHT}*coverage + "
              f"{PERSISTENCE_WEIGHT}*persistence + {EVENT_PARTICIPATION_WEIGHT}*events")
        print(f"  (event participation saturates at {EVENT_PARTICIPATION_SATURATION} unique event types)")
        print("\nThis measures TEXTUAL DOMINANCE, not narrative importance.")
        sys.exit(1)
    
    novel_name = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else "standalone_salience"
    tier2_run_id = sys.argv[3] if len(sys.argv) > 3 else ""
    
    output_path = generate_salience_index(novel_name, run_id, tier2_run_id)
    
    if output_path:
        print(f"\n✓ Salience index generated: {output_path}")
    else:
        print("\n✗ Salience index generation failed")
        sys.exit(1)
