"""
Tag Resolver for Abridge Pipeline (Tier-3.4b)

PURPOSE:
This module resolves TAG SIGNALS from upstream Tier-3 data using deterministic,
rule-based evaluation. It aggregates evidence from character salience, relationship
patterns, event keywords, and genre resolution to produce confidence-scored tag
assignments.

============================================================
WHY TAG DETECTION EXISTS
============================================================

Tags provide granular narrative descriptors. They answer:
"What specific elements characterize this story?"

Tag detection in Abridge is DESCRIPTIVE, not EVALUATIVE:
- It does NOT judge literary quality
- It does NOT interpret authorial intent
- It does NOT collapse to a single "best" tag
- It DOES report which tags have observable evidence

============================================================
WHAT THIS IS
============================================================

This is a DERIVED, RULE-BASED feature that:
- Consumes ONLY Tier-3.1 (Salience), Tier-3.2 (Relationships), Tier-3.3 (Keywords), Tier-3.4a (Genre)
- Applies deterministic rules to compute tag confidence
- Produces multi-tag output with evidence attribution
- Stores results as a read-only Tier-3 artifact

============================================================
WHAT THIS IS NOT (CRITICAL)
============================================================

This feature DOES NOT:
- Use LLMs or semantic similarity
- Match text against tag descriptions
- Interpret narrative meaning
- Force tag assignment when evidence is weak
- Produce a single "primary" tag
- Judge story quality

============================================================
TAG RULE MODEL
============================================================

Each tag is defined by a RULE with:

1. REQUIRED EVIDENCE (hard gate)
   - Specific signals that MUST be present
   - If ANY required evidence is missing → confidence = 0
   - Examples: keyword presence, category presence, genre presence

2. SUPPORTING EVIDENCE (boosts)
   - Signals that INCREASE confidence when present
   - Each boost adds to the score
   - Examples: high narrative spread, persistent keywords, genre alignment

3. PENALTIES (reductions)
   - Signals that DECREASE confidence when present
   - Applied after boosts
   - Examples: contradictory keywords, conflicting genres

All rules are:
- Deterministic (same input → same output)
- Explicit (no hidden logic)
- Versioned (for reproducibility)
- Documented (inline comments explain each rule)

============================================================
CONFIDENCE SCORING
============================================================

Score = base_score + sum(boosts) - sum(penalties)
Final score is clamped to [0.0, 1.0]

base_score: Awarded when ALL required evidence is met
boosts: Added for each supporting evidence item present
penalties: Subtracted for each contradictory signal

============================================================
TAG TAXONOMY
============================================================

Tags are drawn from Feydar/novelupdates_tags taxonomy (curated subset).
Only tags with implementable rules from pipeline evidence are included.
Tag descriptions are for documentation only — NEVER used as classifiers.

Many tags CANNOT be resolved from pipeline data:
- Personality tags requiring interpretation (Dense Protagonist, Naive Protagonist)
- External metadata tags (Award-winning, Adapted to Anime)
- Subjective judgment tags (Cute Protagonist, Charming Protagonist)

Only tags with DETECTABLE EVIDENCE are implemented.

============================================================
CONSUMER WARNING
============================================================

Downstream consumers MUST understand:
- Confidence scores are NOT probabilities
- Multiple tags can have high confidence (multi-tag novels)
- Low confidence means "insufficient evidence", not "definitely not this tag"
- Empty results mean "no tags have sufficient evidence"
- This data enables framing; it does not perform literary analysis

============================================================
STORAGE
============================================================

Tag data is stored per run_id in:
- JSON artifact: data/tag_resolved/{novel_name}/{run_id}.tag_resolved.json

Includes taxonomy version and rule version for reproducibility.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from dict.tag_dictionary import TAG_TAXONOMY_VERSION, TAG_RULE_VERSION, TAG_TAXONOMY, TAG_RULES
load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------

TAG_RESOLVED_DIR = os.getenv(
    "ABRIDGE_TAG_RESOLVED_DIR",
    "data/tag_resolved"
)

CHARACTER_SALIENCE_DIR = os.getenv(
    "ABRIDGE_CHARACTER_SALIENCE_DIR",
    "data/character_salience"
)

RELATIONSHIP_MATRIX_DIR = os.getenv(
    "ABRIDGE_RELATIONSHIP_MATRIX_DIR",
    "data/relationship_matrix"
)

EVENT_KEYWORDS_DIR = os.getenv(
    "ABRIDGE_EVENT_KEYWORDS_DIR",
    "data/event_keywords"
)

GENRE_RESOLVED_DIR = os.getenv(
    "ABRIDGE_GENRE_RESOLVED_DIR",
    "data/genre_resolved"
)

# Minimum confidence threshold for tag inclusion in output
# Conservative: only report tags with meaningful evidence
CONFIDENCE_THRESHOLD = 0.3

# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class TagEvidence:
    """Evidence supporting a tag assignment."""
    event_keywords: list = field(default_factory=list)
    event_categories: list = field(default_factory=list)
    keyword_spreads: dict = field(default_factory=dict)
    keyword_densities: dict = field(default_factory=dict)
    genres_present: list = field(default_factory=list)
    salient_characters: int = 0
    persistent_pairs: int = 0
    penalties_applied: list = field(default_factory=list)


@dataclass
class TagResult:
    """Result for a single tag resolution."""
    tag_id: str
    display_name: str
    confidence: float
    evidence: TagEvidence
    required_met: bool
    base_score: float
    boosts_applied: float
    penalties_applied: float


@dataclass
class TagResolvedMap:
    """Complete tag resolution output for a novel."""
    novel_name: str
    run_id: str
    tier: str = "tier-3.4b"
    taxonomy_version: str = TAG_TAXONOMY_VERSION
    rule_version: str = TAG_RULE_VERSION
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    total_tags_evaluated: int = 0
    tags_above_threshold: int = 0
    tags: dict = field(default_factory=dict)
    input_artifacts: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


# --------------------------------------------------
# Evidence Extraction
# --------------------------------------------------

def _load_event_keywords(novel_name: str, run_id: str) -> Optional[dict]:
    """Load event keywords artifact for the given run."""
    artifact_path = os.path.join(
        EVENT_KEYWORDS_DIR,
        novel_name,
        f"{run_id}.event_keywords.json"
    )
    
    if os.path.exists(artifact_path):
        with open(artifact_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback: find most recent artifact
    novel_dir = os.path.join(EVENT_KEYWORDS_DIR, novel_name)
    if not os.path.exists(novel_dir):
        return None
    
    artifacts = sorted([
        f for f in os.listdir(novel_dir)
        if f.endswith(".event_keywords.json")
    ], reverse=True)
    
    if artifacts:
        with open(os.path.join(novel_dir, artifacts[0]), "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


def _load_character_salience(novel_name: str, run_id: str) -> Optional[dict]:
    """Load character salience artifact for the given run."""
    artifact_path = os.path.join(
        CHARACTER_SALIENCE_DIR,
        novel_name,
        f"{run_id}.character_salience.json"
    )
    
    if os.path.exists(artifact_path):
        with open(artifact_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback: find most recent artifact
    novel_dir = os.path.join(CHARACTER_SALIENCE_DIR, novel_name)
    if not os.path.exists(novel_dir):
        return None
    
    artifacts = sorted([
        f for f in os.listdir(novel_dir)
        if f.endswith(".character_salience.json")
    ], reverse=True)
    
    if artifacts:
        with open(os.path.join(novel_dir, artifacts[0]), "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


def _load_relationship_matrix(novel_name: str, run_id: str) -> Optional[dict]:
    """Load relationship matrix artifact for the given run."""
    artifact_path = os.path.join(
        RELATIONSHIP_MATRIX_DIR,
        novel_name,
        f"{run_id}.relationship_matrix.json"
    )
    
    if os.path.exists(artifact_path):
        with open(artifact_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback: find most recent artifact
    novel_dir = os.path.join(RELATIONSHIP_MATRIX_DIR, novel_name)
    if not os.path.exists(novel_dir):
        return None
    
    artifacts = sorted([
        f for f in os.listdir(novel_dir)
        if f.endswith(".relationship_matrix.json")
    ], reverse=True)
    
    if artifacts:
        with open(os.path.join(novel_dir, artifacts[0]), "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


def _load_genre_resolved(novel_name: str, run_id: str) -> Optional[dict]:
    """Load genre resolved artifact for the given run."""
    artifact_path = os.path.join(
        GENRE_RESOLVED_DIR,
        novel_name,
        f"{run_id}.genre_resolved.json"
    )
    
    if os.path.exists(artifact_path):
        with open(artifact_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback: find most recent artifact
    novel_dir = os.path.join(GENRE_RESOLVED_DIR, novel_name)
    if not os.path.exists(novel_dir):
        return None
    
    artifacts = sorted([
        f for f in os.listdir(novel_dir)
        if f.endswith(".genre_resolved.json")
    ], reverse=True)
    
    if artifacts:
        with open(os.path.join(novel_dir, artifacts[0]), "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


# --------------------------------------------------
# Rule Evaluation Engine
# --------------------------------------------------

class TagRuleEngine:
    """
    Deterministic rule evaluation engine for tag resolution.
    
    This engine applies explicit rules to extract evidence and compute
    confidence scores. All logic is documented and versioned.
    """
    
    def __init__(
        self,
        event_keywords: Optional[dict],
        character_salience: Optional[dict],
        relationship_matrix: Optional[dict],
        genre_resolved: Optional[dict],
    ):
        self.event_keywords = event_keywords or {}
        self.character_salience = character_salience or {}
        self.relationship_matrix = relationship_matrix or {}
        self.genre_resolved = genre_resolved or {}
        
        # Pre-extract commonly used data
        self._keywords = self.event_keywords.get("keywords", {})
        self._categories = self.event_keywords.get("categories_found", {})
        self._characters = self.character_salience.get("characters", [])
        self._pairs = self.relationship_matrix.get("pairs", {})
        self._genres = self.genre_resolved.get("genres", {})
    
    def _check_keyword_present(self, keyword_id: str) -> bool:
        """Check if a keyword exists in the event keywords data."""
        return keyword_id in self._keywords
    
    def _check_category_present(self, category: str) -> bool:
        """Check if a category exists in the event keywords data."""
        return category in self._categories
    
    def _check_keyword_spread(self, keyword_id: str, min_spread: int) -> bool:
        """Check if a keyword has narrative_spread >= min_spread."""
        if keyword_id not in self._keywords:
            return False
        return self._keywords[keyword_id].get("narrative_spread", 0) >= min_spread
    
    def _check_keyword_density(self, keyword_id: str, min_density: float) -> bool:
        """Check if a keyword has density >= min_density."""
        if keyword_id not in self._keywords:
            return False
        return self._keywords[keyword_id].get("density", 0) >= min_density
    
    def _check_category_count(self, category: str, min_count: int) -> bool:
        """Check if a category has >= min_count keywords present."""
        if category not in self._categories:
            return False
        return len(self._categories[category]) >= min_count
    
    def _check_salient_character_count(self, min_count: int, min_salience: float) -> bool:
        """Check if >= min_count characters have salience >= min_salience."""
        count = sum(
            1 for c in self._characters
            if c.get("salience_score", 0) >= min_salience
        )
        return count >= min_count
    
    def _check_salient_pair_persistence(self, min_persistence: float) -> bool:
        """Check if any pair has persistence_score >= min_persistence."""
        for pair_data in self._pairs.values():
            if pair_data.get("persistence_score", 0) >= min_persistence:
                return True
        return False
    
    def _check_high_persistence_pair_count(self, min_count: int, min_persistence: float) -> bool:
        """Check if >= min_count pairs have persistence >= min_persistence."""
        count = sum(
            1 for pair_data in self._pairs.values()
            if pair_data.get("persistence_score", 0) >= min_persistence
        )
        return count >= min_count
    
    def _check_genre_present(self, genre_id: str) -> bool:
        """Check if a genre is present in resolved genres (above threshold)."""
        return genre_id in self._genres
    
    def _check_genre_confidence(self, genre_id: str, min_confidence: float) -> bool:
        """Check if a genre has confidence >= min_confidence."""
        if genre_id not in self._genres:
            return False
        return self._genres[genre_id].get("confidence", 0) >= min_confidence
    
    def _check_condition(self, condition_type: str, condition_value) -> bool:
        """Evaluate a single condition."""
        if condition_type == "keyword_present":
            if isinstance(condition_value, list):
                return any(self._check_keyword_present(kw) for kw in condition_value)
            return self._check_keyword_present(condition_value)
        
        elif condition_type == "category_present":
            if isinstance(condition_value, list):
                return any(self._check_category_present(cat) for cat in condition_value)
            return self._check_category_present(condition_value)
        
        elif condition_type == "keyword_spread":
            keyword_id, min_spread = condition_value
            return self._check_keyword_spread(keyword_id, min_spread)
        
        elif condition_type == "keyword_density":
            keyword_id, min_density = condition_value
            return self._check_keyword_density(keyword_id, min_density)
        
        elif condition_type == "category_count":
            category, min_count = condition_value
            return self._check_category_count(category, min_count)
        
        elif condition_type == "salient_character_count":
            min_count, min_salience = condition_value
            return self._check_salient_character_count(min_count, min_salience)
        
        elif condition_type == "salient_pair_persistence":
            return self._check_salient_pair_persistence(condition_value)
        
        elif condition_type == "high_persistence_pair_count":
            min_count, min_persistence = condition_value
            return self._check_high_persistence_pair_count(min_count, min_persistence)
        
        elif condition_type == "genre_present":
            return self._check_genre_present(condition_value)
        
        elif condition_type == "genre_confidence":
            genre_id, min_confidence = condition_value
            return self._check_genre_confidence(genre_id, min_confidence)
        
        return False
    
    def evaluate_tag(self, tag_id: str, rule: dict) -> TagResult:
        """
        Evaluate a single tag against its rule.
        
        Returns TagResult with confidence score and evidence.
        """
        evidence = TagEvidence()
        required = rule.get("required", {})
        boosts = rule.get("boosts", [])
        penalties = rule.get("penalties", [])
        base_score = rule.get("base_score", 0.3)
        
        # Check required evidence (hard gate)
        required_met = True
        for condition_type, condition_value in required.items():
            if not self._check_condition(condition_type, condition_value):
                required_met = False
                break
        
        if not required_met:
            # Required evidence missing → confidence = 0
            return TagResult(
                tag_id=tag_id,
                display_name=TAG_TAXONOMY.get(tag_id, {}).get("display_name", tag_id),
                confidence=0.0,
                evidence=evidence,
                required_met=False,
                base_score=base_score,
                boosts_applied=0.0,
                penalties_applied=0.0,
            )
        
        # Collect evidence and apply boosts
        total_boosts = 0.0
        
        for condition_type, condition_value, boost_score in boosts:
            if self._check_condition(condition_type, condition_value):
                total_boosts += boost_score
                
                # Record evidence
                if condition_type == "keyword_present":
                    if isinstance(condition_value, str):
                        evidence.event_keywords.append(condition_value)
                elif condition_type == "category_present":
                    if isinstance(condition_value, str):
                        evidence.event_categories.append(condition_value)
                elif condition_type == "keyword_spread":
                    keyword_id, min_spread = condition_value
                    actual_spread = self._keywords.get(keyword_id, {}).get("narrative_spread", 0)
                    evidence.keyword_spreads[keyword_id] = actual_spread
                elif condition_type == "keyword_density":
                    keyword_id, min_density = condition_value
                    actual_density = self._keywords.get(keyword_id, {}).get("density", 0)
                    evidence.keyword_densities[keyword_id] = actual_density
                elif condition_type == "genre_present":
                    evidence.genres_present.append(condition_value)
                elif condition_type == "salient_character_count":
                    min_count, min_salience = condition_value
                    evidence.salient_characters = sum(
                        1 for c in self._characters
                        if c.get("salience_score", 0) >= min_salience
                    )
                elif condition_type in ("salient_pair_persistence", "high_persistence_pair_count"):
                    evidence.persistent_pairs = sum(
                        1 for pair_data in self._pairs.values()
                        if pair_data.get("persistence_score", 0) >= 0.5
                    )
        
        # Apply penalties
        total_penalties = 0.0
        
        for condition_type, condition_value, penalty_score in penalties:
            if self._check_condition(condition_type, condition_value):
                total_penalties += penalty_score
                evidence.penalties_applied.append(f"{condition_type}:{condition_value}")
        
        # Compute final confidence
        confidence = base_score + total_boosts - total_penalties
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        
        return TagResult(
            tag_id=tag_id,
            display_name=TAG_TAXONOMY.get(tag_id, {}).get("display_name", tag_id),
            confidence=round(confidence, 4),
            evidence=evidence,
            required_met=True,
            base_score=base_score,
            boosts_applied=round(total_boosts, 4),
            penalties_applied=round(total_penalties, 4),
        )


# --------------------------------------------------
# Main Pipeline Function
# --------------------------------------------------

def build_tag_resolved_map(
    novel_name: str,
    run_id: str,
    event_keywords: Optional[dict],
    character_salience: Optional[dict],
    relationship_matrix: Optional[dict],
    genre_resolved: Optional[dict],
) -> TagResolvedMap:
    """
    Build the tag resolution map from Tier-3 artifacts.
    
    This function:
    1. Initializes the rule engine with input artifacts
    2. Evaluates each tag against its rule
    3. Filters by confidence threshold
    4. Returns structured output with evidence attribution
    
    Args:
        novel_name: Name of the novel
        run_id: Pipeline run identifier
        event_keywords: Tier-3.3 event keywords artifact
        character_salience: Tier-3.1 salience artifact
        relationship_matrix: Tier-3.2 matrix artifact
        genre_resolved: Tier-3.4a genre resolved artifact
    
    Returns:
        TagResolvedMap with confidence-scored tags
    """
    # Initialize output
    result = TagResolvedMap(
        novel_name=novel_name,
        run_id=run_id,
        warnings=[
            "Confidence scores are NOT probabilities",
            "Multiple tags can have high confidence",
            "Low confidence means 'insufficient evidence'",
            "This data enables framing, not literary analysis",
            "Many tags (personality, subjective) cannot be detected",
        ],
    )
    
    # Track input artifacts used
    result.input_artifacts = {
        "event_keywords": event_keywords is not None,
        "character_salience": character_salience is not None,
        "relationship_matrix": relationship_matrix is not None,
        "genre_resolved": genre_resolved is not None,
    }
    
    # Check if we have minimum required data
    if event_keywords is None:
        result.warnings.append("No event keywords data available - tag resolution limited")
    
    if genre_resolved is None:
        result.warnings.append("No genre resolved data available - some tag rules limited")
    
    # Initialize rule engine
    engine = TagRuleEngine(
        event_keywords=event_keywords,
        character_salience=character_salience,
        relationship_matrix=relationship_matrix,
        genre_resolved=genre_resolved,
    )
    
    # Evaluate all tags
    tag_results = []
    
    for tag_id, rule in TAG_RULES.items():
        tag_result = engine.evaluate_tag(tag_id, rule)
        tag_results.append(tag_result)
    
    result.total_tags_evaluated = len(tag_results)
    
    # Filter by confidence threshold and add to output
    for tr in tag_results:
        if tr.confidence >= CONFIDENCE_THRESHOLD:
            result.tags[tr.tag_id] = {
                "display_name": tr.display_name,
                "confidence": tr.confidence,
                "evidence": {
                    "event_keywords": tr.evidence.event_keywords,
                    "event_categories": tr.evidence.event_categories,
                    "keyword_spreads": tr.evidence.keyword_spreads,
                    "keyword_densities": tr.evidence.keyword_densities,
                    "genres_present": tr.evidence.genres_present,
                    "salient_characters": tr.evidence.salient_characters,
                    "persistent_pairs": tr.evidence.persistent_pairs,
                    "penalties_applied": tr.evidence.penalties_applied,
                },
                "scoring": {
                    "base_score": tr.base_score,
                    "boosts_applied": tr.boosts_applied,
                    "penalties_applied": tr.penalties_applied,
                },
            }
    
    result.tags_above_threshold = len(result.tags)
    
    return result


def generate_tag_resolved(
    novel_name: str,
    run_id: str,
) -> Optional[str]:
    """
    Main pipeline entry point for tag resolution.
    
    Loads Tier-3 artifacts, computes tag confidence scores,
    and persists the result.
    
    Args:
        novel_name: Name of the novel
        run_id: Pipeline run identifier
    
    Returns:
        Path to saved artifact, or None if resolution failed
    """
    print(f"\n[Tag Resolver] Resolving tags from Tier-3 evidence...")
    print(f"[Tag Resolver] Taxonomy version: {TAG_TAXONOMY_VERSION}")
    print(f"[Tag Resolver] Rule version: {TAG_RULE_VERSION}")
    print(f"[Tag Resolver] Confidence threshold: {CONFIDENCE_THRESHOLD}")
    
    # Load input artifacts
    event_keywords = _load_event_keywords(novel_name, run_id)
    character_salience = _load_character_salience(novel_name, run_id)
    relationship_matrix = _load_relationship_matrix(novel_name, run_id)
    genre_resolved = _load_genre_resolved(novel_name, run_id)
    
    # Log artifact status
    if event_keywords:
        print(f"[Tag Resolver] Loaded event keywords: {event_keywords.get('total_keywords_found', 0)} keywords")
    else:
        print(f"[Tag Resolver] WARNING: No event keywords artifact found")
    
    if character_salience:
        print(f"[Tag Resolver] Loaded character salience: {len(character_salience.get('characters', []))} characters")
    else:
        print(f"[Tag Resolver] WARNING: No character salience artifact found")
    
    if relationship_matrix:
        print(f"[Tag Resolver] Loaded relationship matrix: {len(relationship_matrix.get('pairs', {}))} pairs")
    else:
        print(f"[Tag Resolver] WARNING: No relationship matrix artifact found")
    
    if genre_resolved:
        print(f"[Tag Resolver] Loaded genre resolved: {genre_resolved.get('genres_above_threshold', 0)} genres")
    else:
        print(f"[Tag Resolver] WARNING: No genre resolved artifact found")
    
    # Build tag resolution
    result = build_tag_resolved_map(
        novel_name=novel_name,
        run_id=run_id,
        event_keywords=event_keywords,
        character_salience=character_salience,
        relationship_matrix=relationship_matrix,
        genre_resolved=genre_resolved,
    )
    
    # Report results
    print(f"[Tag Resolver] Evaluated {result.total_tags_evaluated} tags")
    print(f"[Tag Resolver] Found {result.tags_above_threshold} tags above threshold")
    
    if result.tags:
        # Sort by confidence descending
        sorted_tags = sorted(
            result.tags.items(),
            key=lambda x: x[1]["confidence"],
            reverse=True
        )
        
        print(f"[Tag Resolver] Top tags:")
        for tag_id, data in sorted_tags[:10]:
            evidence_summary = []
            if data["evidence"]["event_keywords"]:
                evidence_summary.append(f"keywords={data['evidence']['event_keywords']}")
            if data["evidence"]["genres_present"]:
                evidence_summary.append(f"genres={data['evidence']['genres_present']}")
            if data["evidence"]["event_categories"]:
                evidence_summary.append(f"categories={data['evidence']['event_categories']}")
            evidence_str = ", ".join(evidence_summary) if evidence_summary else "base evidence"
            print(f"  - {data['display_name']}: {data['confidence']:.2f} ({evidence_str})")
    else:
        print(f"[Tag Resolver] No tags met the confidence threshold")
    
    # Persist artifact
    output_dir = os.path.join(TAG_RESOLVED_DIR, novel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"{run_id}.tag_resolved.json")
    
    # Convert to dict for JSON serialization
    output_data = {
        "novel_name": result.novel_name,
        "run_id": result.run_id,
        "tier": result.tier,
        "taxonomy_version": result.taxonomy_version,
        "rule_version": result.rule_version,
        "confidence_threshold": result.confidence_threshold,
        "total_tags_evaluated": result.total_tags_evaluated,
        "tags_above_threshold": result.tags_above_threshold,
        "tags": result.tags,
        "input_artifacts": result.input_artifacts,
        "warnings": result.warnings,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"[Tag Resolver] Saved to: {output_path}")
    
    return output_path


# --------------------------------------------------
# Standalone Execution
# --------------------------------------------------

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python tag_resolver.py <novel_name> [run_id]")
        print("  If run_id is omitted, uses 'standalone_tag' as identifier")
        sys.exit(1)
    
    novel_name = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else "standalone_tag"
    
    result_path = generate_tag_resolved(novel_name, run_id)
    
    if result_path:
        print(f"\n✓ Tag resolution generated: {result_path}")
    else:
        print(f"\n✗ Tag resolution failed")
        sys.exit(1)
