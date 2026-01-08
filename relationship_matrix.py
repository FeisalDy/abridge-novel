"""
Relationship Signal Matrix for Abridge Pipeline (Tier-3.2)

PURPOSE:
This module computes STRUCTURAL CO-PRESENCE SIGNALS between character pairs.
It measures which characters PERSISTENTLY APPEAR TOGETHER across the narrative,
NOT relationships, bonds, roles, or any semantic meaning.

============================================================
WHAT THIS IS
============================================================

This is a DERIVED, OBSERVATIONAL feature that:
- Consumes ONLY Tier-2 (Surface Index) and Tier-3.1 (Salience Index) data
- Computes deterministic pairwise co-presence metrics
- Produces a symmetric matrix of structural signals
- Stores results as a read-only Tier-3 artifact

============================================================
WHAT THIS IS NOT (CRITICAL)
============================================================

This feature DOES NOT:
- Infer relationship types (romance, rivalry, alliance, etc.)
- Label character roles or dynamics
- Use emotional or sentiment cues
- Interpret why characters appear together
- Create social graphs or network visualizations
- Merge or resolve character identities

Co-presence means TEXTUAL PROXIMITY, not NARRATIVE CONNECTION.
Characters may co-appear because they're in the same scene,
or merely mentioned in the same chapter — nothing more.

============================================================
SIGNAL DEFINITIONS (DOCUMENTED)
============================================================

For each qualifying character pair (A, B):

1. CO_PRESENCE_COUNT
   - Number of chapters where BOTH A and B appear
   - Formula: len(A.chapters ∩ B.chapters)

2. CO_PRESENCE_RATIO
   - Co-presence relative to the less-covered character
   - Formula: co_presence_count / min(A.coverage, B.coverage)
   - Range: [0.0, 1.0]
   - Interpretation: 1.0 means whenever the rarer character appears,
     the other is always present

3. JACCARD_SIMILARITY
   - Standard set similarity metric
   - Formula: |A.chapters ∩ B.chapters| / |A.chapters ∪ B.chapters|
   - Range: [0.0, 1.0]
   - Interpretation: How similar are their chapter distributions

4. NARRATIVE_SPAN
   - Distance from first to last co-presence (in chapters)
   - Formula: max_co_chapter_index - min_co_chapter_index + 1
   - Measures how much of the narrative they span together

5. PERSISTENCE_SCORE
   - Composite score rewarding distributed co-presence
   - Penalizes clustered appearances, rewards spread
   - Formula: (co_presence_ratio * span_ratio * density_factor)
   - Normalized to [0.0, 1.0]

============================================================
PAIR ELIGIBILITY (CONFIGURABLE)
============================================================

To prevent O(N²) explosion with large casts:

- Only characters with salience_score >= SALIENCE_THRESHOLD are included
- Default threshold: 0.1 (top ~90% of characters by salience)
- This is CONSERVATIVE: includes most characters, excludes only noise

Excluded characters are documented in output for auditability.

============================================================
CONSUMER WARNING
============================================================

Downstream consumers MUST understand:
- Co-presence is STRUCTURAL, not semantic
- High persistence does NOT mean "close relationship"
- This data enables pattern detection; it does not interpret
- All signals are relative within a single novel/run

============================================================
STORAGE
============================================================

Matrix data is stored per run_id in:
- JSON artifact: data/relationship_matrix/{novel_name}/{run_id}.relationship_matrix.json

This artifact is marked as Tier-3.2 (derived) and never overwrites previous runs.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from itertools import combinations
from dotenv import load_dotenv
load_dotenv()

# --------------------------------------------------
# Configuration: Thresholds and Weights
# --------------------------------------------------

# SALIENCE_THRESHOLD: Minimum salience score to include a character in pairing
# Characters below this threshold are excluded to prevent combinatorial explosion.
# Default 0.1 means only characters with less than 10% of max salience are excluded.
# This is CONSERVATIVE by design - we include most characters.
SALIENCE_THRESHOLD = 0.1

# MINIMUM_CO_PRESENCE: Minimum chapters of co-presence to create a pair entry
# Pairs with fewer co-presence chapters are excluded as noise.
# Default 1 means at least one shared chapter is required.
MINIMUM_CO_PRESENCE = 1

# Persistence score weights
# These control how the composite persistence score is calculated
PERSISTENCE_RATIO_WEIGHT = 0.4    # Weight for co_presence_ratio
PERSISTENCE_SPAN_WEIGHT = 0.3     # Weight for span coverage
PERSISTENCE_DENSITY_WEIGHT = 0.3  # Weight for distribution density


# --------------------------------------------------
# Configuration: Paths
# --------------------------------------------------

RELATIONSHIP_MATRIX_DIR = os.getenv(
    "ABRIDGE_RELATIONSHIP_MATRIX_DIR",
    "data/relationship_matrix"
)

CHARACTER_INDEX_DIR = os.getenv(
    "ABRIDGE_CHARACTER_INDEX_DIR",
    "data/character_index"
)

CHARACTER_SALIENCE_DIR = os.getenv(
    "ABRIDGE_CHARACTER_SALIENCE_DIR",
    "data/character_salience"
)


# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class PairSignal:
    """
    Structural co-presence signals for a character pair.
    
    WARNING: These are STRUCTURAL metrics, not relationship indicators.
    High co-presence does NOT mean characters are related in the narrative.
    """
    # Pair identification (alphabetically sorted for consistency)
    character_a: str
    character_b: str
    
    # Raw metrics
    co_presence_count: int          # Chapters where both appear
    character_a_coverage: int       # Chapters where A appears
    character_b_coverage: int       # Chapters where B appears
    union_coverage: int             # Chapters where A or B appears
    
    # First and last co-presence (0-based chapter indices)
    first_co_presence_index: int
    last_co_presence_index: int
    
    # Derived signals (all 0.0-1.0)
    co_presence_ratio: float        # co_presence / min(coverage)
    jaccard_similarity: float       # intersection / union
    span_ratio: float               # span / total_chapters
    persistence_score: float        # Composite score
    
    def pair_key(self) -> str:
        """Return canonical pair key (alphabetically sorted)."""
        return f"{self.character_a}|{self.character_b}"


@dataclass
class RelationshipSignalMatrix:
    """
    Complete relationship signal matrix for a novel run.
    
    This is a TIER-3.2 DERIVED ARTIFACT.
    It measures structural co-presence, NOT relationships.
    """
    # Identification
    novel_name: str
    run_id: str
    tier: str = "tier-3.2"
    
    # Source data references
    source_tier2_run_id: str = ""
    source_tier3_1_run_id: str = ""
    
    # Configuration used (for reproducibility)
    config: dict = field(default_factory=lambda: {
        "salience_threshold": SALIENCE_THRESHOLD,
        "minimum_co_presence": MINIMUM_CO_PRESENCE,
        "persistence_weights": {
            "ratio": PERSISTENCE_RATIO_WEIGHT,
            "span": PERSISTENCE_SPAN_WEIGHT,
            "density": PERSISTENCE_DENSITY_WEIGHT,
        },
    })
    
    # Novel metadata
    total_chapters: int = 0
    total_characters_considered: int = 0
    total_characters_excluded: int = 0
    total_pairs: int = 0
    
    # Excluded characters (for auditability)
    excluded_characters: list[str] = field(default_factory=list)
    exclusion_reason: str = "salience_score below threshold"
    
    # Pair signals (keyed by "CharA|CharB" for quick lookup)
    pairs: dict[str, PairSignal] = field(default_factory=dict)
    
    # Warnings for downstream consumers
    warnings: list[str] = field(default_factory=lambda: [
        "Co-presence is STRUCTURAL, not semantic",
        "High persistence does NOT indicate close relationships",
        "Signals measure textual proximity, not narrative connection",
        "This is evidence for pattern detection, not interpretation",
    ])


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def _parse_chapter_index(chapter_id: str) -> int:
    """Extract numeric index from chapter identifier (0-based)."""
    import re
    match = re.search(r'(\d+)', chapter_id)
    if match:
        return int(match.group(1)) - 1
    return 0


def _canonical_pair_key(name_a: str, name_b: str) -> tuple[str, str]:
    """Return names in canonical (alphabetically sorted) order."""
    if name_a <= name_b:
        return (name_a, name_b)
    return (name_b, name_a)


# --------------------------------------------------
# Signal Computation
# --------------------------------------------------

def _compute_co_presence_metrics(
    chapters_a: set[str],
    chapters_b: set[str],
) -> tuple[int, int, int, set[str]]:
    """
    Compute basic co-presence metrics for a character pair.
    
    Returns:
        (co_presence_count, coverage_a, coverage_b, co_chapters)
    """
    co_chapters = chapters_a & chapters_b
    return (
        len(co_chapters),
        len(chapters_a),
        len(chapters_b),
        co_chapters,
    )


def _compute_co_presence_ratio(
    co_presence_count: int,
    coverage_a: int,
    coverage_b: int,
) -> float:
    """
    Compute co-presence ratio.
    
    Formula: co_presence_count / min(coverage_a, coverage_b)
    
    This measures: "When the less-frequent character appears,
    how often does the other character also appear?"
    
    Range: [0.0, 1.0]
    """
    min_coverage = min(coverage_a, coverage_b)
    if min_coverage == 0:
        return 0.0
    return co_presence_count / min_coverage


def _compute_jaccard_similarity(
    co_presence_count: int,
    coverage_a: int,
    coverage_b: int,
) -> float:
    """
    Compute Jaccard similarity coefficient.
    
    Formula: |A ∩ B| / |A ∪ B|
    
    This is a standard set similarity metric.
    
    Range: [0.0, 1.0]
    """
    union_size = coverage_a + coverage_b - co_presence_count
    if union_size == 0:
        return 0.0
    return co_presence_count / union_size


def _compute_span_metrics(
    co_chapters: set[str],
    total_chapters: int,
) -> tuple[int, int, float]:
    """
    Compute narrative span metrics for co-presence.
    
    Returns:
        (first_co_index, last_co_index, span_ratio)
    """
    if not co_chapters:
        return (0, 0, 0.0)
    
    indices = [_parse_chapter_index(ch) for ch in co_chapters]
    first_idx = min(indices)
    last_idx = max(indices)
    span = last_idx - first_idx + 1
    
    span_ratio = span / total_chapters if total_chapters > 0 else 0.0
    
    return (first_idx, last_idx, span_ratio)


def _compute_persistence_score(
    co_presence_ratio: float,
    span_ratio: float,
    co_presence_count: int,
    span: int,
) -> float:
    """
    Compute composite persistence score.
    
    This score rewards:
    - High co-presence ratio (characters appear together when either appears)
    - Wide narrative span (co-presence spans the story)
    - Distributed presence (not clustered in one section)
    
    Formula:
        persistence = (ratio_weight * co_presence_ratio) +
                      (span_weight * span_ratio) +
                      (density_weight * density_factor)
    
    Where density_factor = co_presence_count / span (how densely they co-appear)
    
    Range: [0.0, 1.0] (clamped)
    """
    # Density: how consistently they appear together within their span
    density_factor = co_presence_count / span if span > 0 else 0.0
    
    # Weighted combination
    score = (
        PERSISTENCE_RATIO_WEIGHT * co_presence_ratio +
        PERSISTENCE_SPAN_WEIGHT * span_ratio +
        PERSISTENCE_DENSITY_WEIGHT * density_factor
    )
    
    # Clamp to [0.0, 1.0]
    return min(1.0, max(0.0, score))


def compute_pair_signal(
    name_a: str,
    name_b: str,
    chapters_a: set[str],
    chapters_b: set[str],
    total_chapters: int,
) -> Optional[PairSignal]:
    """
    Compute all co-presence signals for a character pair.
    
    Returns None if co-presence is below minimum threshold.
    """
    # Ensure canonical ordering
    char_a, char_b = _canonical_pair_key(name_a, name_b)
    if char_a == name_b:
        # Swap chapter sets to match canonical order
        chapters_a, chapters_b = chapters_b, chapters_a
    
    # Compute basic metrics
    co_count, cov_a, cov_b, co_chapters = _compute_co_presence_metrics(
        chapters_a, chapters_b
    )
    
    # Check minimum threshold
    if co_count < MINIMUM_CO_PRESENCE:
        return None
    
    # Compute derived signals
    co_ratio = _compute_co_presence_ratio(co_count, cov_a, cov_b)
    jaccard = _compute_jaccard_similarity(co_count, cov_a, cov_b)
    first_idx, last_idx, span_ratio = _compute_span_metrics(co_chapters, total_chapters)
    
    span = last_idx - first_idx + 1 if co_chapters else 0
    persistence = _compute_persistence_score(co_ratio, span_ratio, co_count, span)
    
    return PairSignal(
        character_a=char_a,
        character_b=char_b,
        co_presence_count=co_count,
        character_a_coverage=cov_a,
        character_b_coverage=cov_b,
        union_coverage=cov_a + cov_b - co_count,
        first_co_presence_index=first_idx,
        last_co_presence_index=last_idx,
        co_presence_ratio=round(co_ratio, 4),
        jaccard_similarity=round(jaccard, 4),
        span_ratio=round(span_ratio, 4),
        persistence_score=round(persistence, 4),
    )


# --------------------------------------------------
# Main Computation
# --------------------------------------------------

def build_relationship_matrix(
        tier2_data: dict,
        tier3_1_data: dict,
        novel_name: str,
        run_id: str,
        tier2_run_id: str,
        tier3_1_run_id: str,
        salience_threshold: float = SALIENCE_THRESHOLD,
) -> RelationshipSignalMatrix:
    """
    Build the relationship signal matrix, sorted by character salience (rank).
    """
    # 1. Extract character data from Tier-2
    tier2_characters = {
        c["name"]: set(c.get("chapters_present", []))
        for c in tier2_data.get("characters", [])
    }

    # 2. Extract salience scores from Tier-3.1
    salience_scores = {
        c["name"]: c.get("salience_score", 0.0)
        for c in tier3_1_data.get("characters", [])
    }

    # Determine total chapters
    all_chapters = set()
    for chapters in tier2_characters.values():
        all_chapters.update(chapters)
    total_chapters = len(all_chapters) if all_chapters else 1

    # 3. Filter characters by salience threshold
    included_characters = []
    excluded_characters = []

    for name in tier2_characters:
        salience = salience_scores.get(name, 0.0)
        if salience >= salience_threshold:
            included_characters.append(name)
        else:
            excluded_characters.append(name)

    # --- CHANGE START: SORT BY SALIENCE (RANK) ---
    # Instead of .sort() (alphabetical), we sort by salience score descending.
    # This ensures "Xu Mo" (1.0) comes before "Origami" (0.44).
    included_characters.sort(key=lambda name: salience_scores.get(name, 0.0), reverse=True)
    # --- CHANGE END ---

    excluded_characters.sort()  # Keeping excluded alphabetical is fine

    # 4. Compute pairwise signals
    # Because included_characters is sorted by Rank, the combinations will
    # follow that order: (Rank1, Rank2), (Rank1, Rank3)... (Rank2, Rank3), etc.
    pairs = {}
    for name_a, name_b in combinations(included_characters, 2):
        chapters_a = tier2_characters.get(name_a, set())
        chapters_b = tier2_characters.get(name_b, set())

        signal = compute_pair_signal(
            name_a, name_b,
            chapters_a, chapters_b,
            total_chapters,
        )

        if signal is not None:
            # Note: signal.pair_key() still uses alphabetical order for the string key
            # but the order they appear in the JSON will match our salience sort.
            pairs[signal.pair_key()] = signal

    # Build matrix
    matrix = RelationshipSignalMatrix(
        novel_name=novel_name,
        run_id=run_id,
        source_tier2_run_id=tier2_run_id,
        source_tier3_1_run_id=tier3_1_run_id,
        total_chapters=total_chapters,
        total_characters_considered=len(included_characters),
        total_characters_excluded=len(excluded_characters),
        total_pairs=len(pairs),
        excluded_characters=excluded_characters,
        pairs=pairs,
    )

    matrix.config["salience_threshold"] = salience_threshold

    return matrix


# --------------------------------------------------
# Data Loading
# --------------------------------------------------

def load_tier2_index(novel_name: str, run_id: str = "") -> Optional[tuple[dict, str]]:
    """Load Tier-2 Character Surface Index data."""
    index_dir = os.path.join(CHARACTER_INDEX_DIR, novel_name)
    
    if not os.path.isdir(index_dir):
        return None
    
    if run_id:
        target_file = os.path.join(index_dir, f"{run_id}.character_index.json")
        if os.path.isfile(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                return json.load(f), run_id
    
    # Find most recent
    index_files = [f for f in os.listdir(index_dir) if f.endswith(".character_index.json")]
    if not index_files:
        return None
    
    index_files.sort(key=lambda f: os.path.getmtime(os.path.join(index_dir, f)), reverse=True)
    latest = index_files[0]
    source_id = latest.replace(".character_index.json", "")
    
    with open(os.path.join(index_dir, latest), 'r', encoding='utf-8') as f:
        return json.load(f), source_id


def load_tier3_1_index(novel_name: str, run_id: str = "") -> Optional[tuple[dict, str]]:
    """Load Tier-3.1 Character Salience Index data."""
    index_dir = os.path.join(CHARACTER_SALIENCE_DIR, novel_name)
    
    if not os.path.isdir(index_dir):
        return None
    
    if run_id:
        target_file = os.path.join(index_dir, f"{run_id}.character_salience.json")
        if os.path.isfile(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                return json.load(f), run_id
    
    # Find most recent
    index_files = [f for f in os.listdir(index_dir) if f.endswith(".character_salience.json")]
    if not index_files:
        return None
    
    index_files.sort(key=lambda f: os.path.getmtime(os.path.join(index_dir, f)), reverse=True)
    latest = index_files[0]
    source_id = latest.replace(".character_salience.json", "")
    
    with open(os.path.join(index_dir, latest), 'r', encoding='utf-8') as f:
        return json.load(f), source_id


# --------------------------------------------------
# Persistence
# --------------------------------------------------

def save_relationship_matrix(
    matrix: RelationshipSignalMatrix,
    novel_name: str,
    run_id: str,
) -> str:
    """
    Save the relationship matrix as a JSON artifact.
    
    Path: data/relationship_matrix/{novel_name}/{run_id}.relationship_matrix.json
    """
    output_dir = os.path.join(RELATIONSHIP_MATRIX_DIR, novel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{run_id}.relationship_matrix.json")
    
    # Convert to dict, handling PairSignal objects
    matrix_dict = asdict(matrix)
    
    # Convert pairs dict (PairSignal objects become dicts via asdict)
    # Already handled by asdict recursively
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matrix_dict, f, indent=2, ensure_ascii=False, sort_keys=False)
    
    return output_file


# --------------------------------------------------
# Pipeline Integration
# --------------------------------------------------

def generate_relationship_matrix(
    novel_name: str,
    run_id: str,
    tier2_run_id: str = "",
    tier3_1_run_id: str = "",
    salience_threshold: float = SALIENCE_THRESHOLD,
) -> Optional[str]:
    """
    Generate and save the relationship signal matrix.
    
    This is the main entry point for pipeline integration.
    NON-BLOCKING: failures are logged but do not halt the pipeline.
    
    Args:
        novel_name: Name of the novel
        run_id: Current pipeline run ID
        tier2_run_id: Specific Tier-2 run to use (or empty for latest)
        tier3_1_run_id: Specific Tier-3.1 run to use (or empty for latest)
        salience_threshold: Minimum salience to include character
        
    Returns:
        Path to saved artifact, or None if generation failed
    """
    try:
        print("\n[Relationship Matrix] Computing character pair signals...")
        
        # Load Tier-2 data
        tier2_result = load_tier2_index(novel_name, tier2_run_id)
        if tier2_result is None:
            print("[Relationship Matrix] ⚠️ No Tier-2 character index found")
            print("[Relationship Matrix] Run with --character-index first")
            return None
        tier2_data, actual_tier2_id = tier2_result
        print(f"[Relationship Matrix] Using Tier-2 data from: {actual_tier2_id}")
        
        # Load Tier-3.1 data
        tier3_1_result = load_tier3_1_index(novel_name, tier3_1_run_id)
        if tier3_1_result is None:
            print("[Relationship Matrix] ⚠️ No Tier-3.1 salience index found")
            print("[Relationship Matrix] Run with --character-salience first")
            return None
        tier3_1_data, actual_tier3_1_id = tier3_1_result
        print(f"[Relationship Matrix] Using Tier-3.1 data from: {actual_tier3_1_id}")
        
        # Build matrix
        matrix = build_relationship_matrix(
            tier2_data=tier2_data,
            tier3_1_data=tier3_1_data,
            novel_name=novel_name,
            run_id=run_id,
            tier2_run_id=actual_tier2_id,
            tier3_1_run_id=actual_tier3_1_id,
            salience_threshold=salience_threshold,
        )
        
        # Save artifact
        output_path = save_relationship_matrix(matrix, novel_name, run_id)
        
        print(f"[Relationship Matrix] Considered {matrix.total_characters_considered} characters "
              f"(excluded {matrix.total_characters_excluded} below salience threshold)")
        print(f"[Relationship Matrix] Found {matrix.total_pairs} character pairs with co-presence")
        print(f"[Relationship Matrix] Saved to: {output_path}")
        
        # Print top pairs for quick inspection
        if matrix.pairs:
            print("[Relationship Matrix] Top 5 pairs by persistence score:")
            sorted_pairs = sorted(
                matrix.pairs.values(),
                key=lambda p: (-p.persistence_score, p.pair_key())
            )
            for pair in sorted_pairs[:5]:
                print(f"  - {pair.character_a} | {pair.character_b}: "
                      f"persistence={pair.persistence_score:.3f} "
                      f"(co-presence={pair.co_presence_count}, "
                      f"ratio={pair.co_presence_ratio:.2f}, "
                      f"jaccard={pair.jaccard_similarity:.2f})")
        
        return output_path
        
    except Exception as e:
        print(f"[Relationship Matrix] ⚠️ Failed to generate matrix: {e}")
        return None


# --------------------------------------------------
# Standalone Execution
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python relationship_matrix.py <novel_name> [run_id] [salience_threshold]")
        print("\nComputes Relationship Signal Matrix (Tier-3.2) from Tier-2 and Tier-3.1 data.")
        print("\nExample:")
        print('  python relationship_matrix.py "Heaven Reincarnation"')
        print('  python relationship_matrix.py "Heaven Reincarnation" "my_run_id"')
        print('  python relationship_matrix.py "Heaven Reincarnation" "my_run_id" 0.05')
        print(f"\nDefault salience threshold: {SALIENCE_THRESHOLD}")
        print("\nThis measures STRUCTURAL CO-PRESENCE, not relationships.")
        sys.exit(1)
    
    novel_name = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else "standalone_matrix"
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else SALIENCE_THRESHOLD
    
    output_path = generate_relationship_matrix(
        novel_name, run_id,
        salience_threshold=threshold,
    )
    
    if output_path:
        print(f"\n✓ Relationship matrix generated: {output_path}")
    else:
        print("\n✗ Relationship matrix generation failed")
        sys.exit(1)
