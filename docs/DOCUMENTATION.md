# Abridge Pipeline — Technical Documentation

**Version:** 1.0.0  
**Last Updated:** 2024-12-31

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Core Pipeline](#3-core-pipeline)
   - [3.1 Chapter Condensation](#31-chapter-condensation)
   - [3.2 Arc Condensation](#32-arc-condensation)
   - [3.3 Novel Condensation](#33-novel-condensation)
   - [3.4 Condensation Prompt](#34-condensation-prompt)
4. [Tier-1: Operational Features](#4-tier-1-operational-features)
   - [4.1 Resume/Skip Flags](#41-resumeskip-flags)
   - [4.2 Cost Tracking](#42-cost-tracking)
   - [4.3 Guardrails](#43-guardrails)
   - [4.4 Run Reports](#44-run-reports)
5. [Tier-2: Structural Features](#5-tier-2-structural-features)
   - [5.1 Character Surface Index](#51-character-surface-index)
6. [Tier-3: Reader-Facing Intelligence](#6-tier-3-reader-facing-intelligence)
   - [6.1 Character Salience](#61-character-salience)
   - [6.2 Relationship Signal Matrix](#62-relationship-signal-matrix)
   - [6.3 Event Keywords](#63-event-keywords)
   - [6.4 Genre Resolver](#64-genre-resolver)
   - [6.5 Tag Resolver](#65-tag-resolver)
7. [Utilities](#7-utilities)
8. [Artifact Reference](#8-artifact-reference)
9. [LLM Provider Configuration](#9-llm-provider-configuration)
10. [CLI Reference](#10-cli-reference)

---

## 1. Overview

**Abridge** is a hierarchical text condensation pipeline designed to reduce long-form novels into progressively shorter summaries while preserving narrative structure, key events, and character information.

### Design Principles

1. **Deterministic Processing**: Same input → same output (excluding LLM variance)
2. **Non-Blocking Failures**: Optional features fail gracefully without halting the pipeline
3. **Audit Trail**: All operations persist signals for post-run analysis
4. **Explicit Configuration**: No auto-magic; all behavior requires explicit flags
5. **Separation of Concerns**: Features are observational, not interpretive

### Pipeline Flow

```
Raw Chapters → Chapter Condensation → Arc Condensation → Novel Condensation
                      ↓
               [Tier-2] Character Index
                      ↓
               [Tier-3.1] Salience → [Tier-3.2] Relationships
                      ↓
               [Tier-3.3] Event Keywords
                      ↓
               [Tier-3.4a] Genre Resolver → [Tier-3.4b] Tag Resolver
```

---

## 2. Architecture

### Directory Structure

```
data/
├── raw/{novel_name}/                  # Input: Raw chapter files
├── chapters_condensed/{novel_name}/   # Stage 1 output
├── arcs_condensed/{novel_name}/       # Stage 2 output
├── novel_condensed/{novel_name}/      # Stage 3 output
├── character_index/{novel_name}/      # Tier-2 output
├── character_salience/{novel_name}/   # Tier-3.1 output
├── relationship_matrix/{novel_name}/  # Tier-3.2 output
├── event_keywords/{novel_name}/       # Tier-3.3 output
├── genre_resolved/{novel_name}/       # Tier-3.4a output
├── tag_resolved/{novel_name}/         # Tier-3.4b output
└── reports/                           # Unified run reports
```

### Persistence

| Data Type | Storage | Purpose |
|-----------|---------|---------|
| Guardrails | SQLite (`abridge_guardrails.db`) | Length ratio events |
| Cost Tracking | SQLite (`abridge_guardrails.db`) | Token usage events |
| Tier-2/3 Artifacts | JSON files | Feature outputs |
| Run Reports | JSON + Markdown | Audit summaries |

---

## 3. Core Pipeline

### 3.1 Chapter Condensation

**Source:** [chapter_condensation.py](../chapter_condensation.py)

#### Purpose

Condense individual raw chapter files into shorter versions using LLM-based summarization.

#### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Raw chapters | `data/raw/{novel_name}/chapter_*.txt` | Plain text |

#### Processing

1. Load raw chapter text
2. Estimate token count using `estimate_tokens()`
3. Apply `BASE_CONDENSATION_PROMPT` via LLM
4. Retry on failure (up to `MAX_LLM_RETRIES=3`)
5. Record guardrail event (length ratio)
6. Write condensed output

#### Outputs

| Output | Location | Format |
|--------|----------|--------|
| Condensed chapters | `data/chapters_condensed/{novel_name}/chapter_*.condensed.txt` | Plain text |

#### Dependencies

- LLM provider (configured via `LLM_PROVIDER` env var)
- Guardrails module (for monitoring)
- Cost tracking module (for usage logging)

#### Constraints / Non-Goals

- **1:1 correspondence**: Each raw chapter produces exactly one condensed chapter
- **NO structural interpretation**: Does not group chapters into arcs
- **NO character analysis**: Does not extract character information
- **NO cross-chapter awareness**: Each chapter processed independently

#### Example Artifact

```
# Input: chapter_001.txt (5,000 words)
# Output: chapter_001.condensed.txt (1,500 words, ratio ~0.30)
```

---

### 3.2 Arc Condensation

**Source:** [arc_condensation.py](../arc_condensation.py)

#### Purpose

Group condensed chapters into arcs and produce arc-level summaries.

#### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Condensed chapters | `data/chapters_condensed/{novel_name}/` | Plain text |

#### Processing

1. Load all condensed chapters in sorted order
2. Group into arcs of `CHAPTERS_PER_ARC=10` chapters each
3. Concatenate chapter texts within each arc
4. Apply `BASE_CONDENSATION_PROMPT` via LLM
5. Record guardrail event (length ratio)
6. Write arc-level output

#### Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `CHAPTERS_PER_ARC` | 10 | Fixed grouping size |

#### Outputs

| Output | Location | Format |
|--------|----------|--------|
| Condensed arcs | `data/arcs_condensed/{novel_name}/arc_*.condensed.txt` | Plain text |

#### Dependencies

- Chapter condensation outputs (required)
- LLM provider
- Guardrails module

#### Constraints / Non-Goals

- **Fixed grouping**: CHAPTERS_PER_ARC is hardcoded
- **NO overlap**: Each chapter belongs to exactly one arc
- **NO semantic grouping**: Arcs are positional, not thematic

---

### 3.3 Novel Condensation

**Source:** [novel_condensation.py](../novel_condensation.py)

#### Purpose

Produce a final, whole-novel summary from arc-level condensations.

#### Inputs

| Input | Source | Format |
|-------|--------|--------|
| Condensed arcs | `data/arcs_condensed/{novel_name}/` | Plain text |

#### Processing

1. Load all condensed arcs in sorted order
2. Concatenate all arc texts
3. Apply `reduce_until_fit()` for scalability:
   - If input exceeds token limit, recursively reduce in halves
   - Base case: input fits within limit → single LLM call
4. Apply `BASE_CONDENSATION_PROMPT` via LLM
5. Write final novel condensation

#### Scalability Algorithm

```python
def reduce_until_fit(text, max_tokens):
    if estimate_tokens(text) <= max_tokens:
        return llm_condense(text)
    
    # Split into halves, reduce each
    mid = len(text) // 2
    left = reduce_until_fit(text[:mid], max_tokens)
    right = reduce_until_fit(text[mid:], max_tokens)
    
    # Combine and reduce again
    return reduce_until_fit(left + right, max_tokens)
```

#### Outputs

| Output | Location | Format |
|--------|----------|--------|
| Novel condensation | `data/novel_condensed/{novel_name}/novel.condensed.txt` | Plain text |

#### Dependencies

- Arc condensation outputs (required)
- `utils.reduce_until_fit()` function
- LLM provider

---

### 3.4 Condensation Prompt

**Source:** [prompt.py](../prompt.py)

#### Purpose

Provide a single, consistent prompt for all condensation stages.

#### BASE_CONDENSATION_PROMPT

The prompt defines a "disciplined literary editor" role with specific rules:

**Preservation Rules:**
1. Keep all key events in chronological order
2. Preserve cause-and-effect relationships
3. Maintain character names exactly as written
4. Keep dialogue only if plot-critical

**Removal Rules:**
1. Remove filler words and redundant descriptions
2. Remove repetitive internal monologue
3. Remove cultivation/training minutiae (unless breakthrough)
4. Remove system notification spam (keep first occurrence)

**Style Rules:**
1. Third-person past tense
2. Neutral, factual tone
3. No editorializing or interpretation
4. No invented content

#### Usage

```python
from prompt import BASE_CONDENSATION_PROMPT

prompt = f"{BASE_CONDENSATION_PROMPT}\n\nText to condense:\n{chapter_text}"
response = llm.generate(prompt)
```

---

## 4. Tier-1: Operational Features

### 4.1 Resume/Skip Flags

**Source:** [run_pipeline.py](../run_pipeline.py)

#### Purpose

Allow users to skip completed stages when re-running the pipeline, avoiding redundant LLM calls.

#### Available Flags

| Flag | Effect |
|------|--------|
| `--skip-chapters` | Reuse existing condensed chapters |
| `--skip-arcs` | Reuse existing condensed arcs |
| `--skip-novel` | Reuse existing novel condensation |

#### Validation Requirements

Before allowing a skip, the pipeline validates:

**Chapter Skip Validation:**
- Condensed chapter directory exists
- Count of condensed chapters matches count of raw chapters

**Arc Skip Validation:**
- Arc directory exists
- At least one arc file present

**Novel Skip Validation:**
- Novel condensation file exists
- File is non-empty

#### Safety Model

- Skipping is **NEVER automatic**
- Skipping requires **explicit flags AND valid outputs**
- Invalid outputs → pipeline **raises error** (does not silently continue)

#### Usage

```bash
# Skip chapters (reuse existing), regenerate arcs and novel
python run_pipeline.py "Novel Name" --skip-chapters

# Skip all condensation, only run Tier-2/3 features
python run_pipeline.py "Novel Name" --skip-chapters --skip-arcs --skip-novel --character-index
```

---

### 4.2 Cost Tracking

**Source:** [cost_tracking.py](../cost_tracking.py)

#### Purpose

Track LLM token usage and estimate costs per run.

#### Data Model

**LLM Usage Event:**
```python
@dataclass
class LLMUsageEvent:
    run_id: str
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    stage: str  # "chapter", "arc", "novel"
    chapter_id: Optional[str]
```

#### Pricing Configuration

```python
MODEL_PRICING = {
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    # ... additional models
}
# Prices are per 1M tokens
```

#### Cost Formula

```
estimated_cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
```

#### Persistence

- Table: `llm_usage_events` in `abridge_guardrails.db`
- Non-blocking: tracking failures do not halt the pipeline

#### Usage

```python
from cost_tracking import log_llm_usage, print_usage_summary

log_llm_usage(
    run_id=run_id,
    provider="gemini",
    model="gemini-2.0-flash-exp",
    input_tokens=1500,
    output_tokens=500,
    stage="chapter",
    chapter_id="chapter_001"
)

# At end of run:
print_usage_summary(run_id)
```

---

### 4.3 Guardrails

**Source:** [guardrails.py](../guardrails.py)

#### Purpose

Monitor condensation quality through length ratio analysis. Detect anomalous compression (too aggressive or too weak).

#### Length Ratio Formula

```
length_ratio = len(condensed_text) / len(original_text)
```

#### Classification Thresholds

**Chapter-Level:**
| Classification | Ratio Range | Interpretation |
|----------------|-------------|----------------|
| GREEN | 0.40 – 0.70 | Expected compression |
| YELLOW | 0.30 – 0.40 OR 0.70 – 0.85 | Unusual but acceptable |
| RED | < 0.30 OR > 0.85 | Anomalous compression |

**Arc-Level:**
| Classification | Ratio Range | Interpretation |
|----------------|-------------|----------------|
| GREEN | 0.25 – 0.50 | Expected compression |
| YELLOW | 0.15 – 0.25 OR 0.50 – 0.65 | Unusual but acceptable |
| RED | < 0.15 OR > 0.65 | Anomalous compression |

#### Non-Blocking Design

Guardrails are **observational only**:
- They record events but never halt the pipeline
- RED classifications are warnings, not errors
- Post-run analysis determines if action is needed

#### Persistence

```sql
CREATE TABLE guardrail_events (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,        -- 'chapter' or 'arc'
    chapter_id TEXT,
    original_length INTEGER,
    condensed_length INTEGER,
    length_ratio REAL,
    classification TEXT         -- 'GREEN', 'YELLOW', 'RED'
);
```

#### Run Summary Output

```
=== Guardrail Summary for run abc123 ===
Total events: 15
Classifications:
  GREEN: 12 (80.0%)
  YELLOW: 2 (13.3%)
  RED: 1 (6.7%)
```

---

### 4.4 Run Reports

**Source:** [run_report.py](../run_report.py)

#### Purpose

Generate unified audit artifacts aggregating guardrails, cost tracking, and pipeline metadata.

#### Data Model

```python
@dataclass
class RunReport:
    run_id: str
    novel_name: str
    timestamp_start: str
    timestamp_end: str
    duration_seconds: float
    llm_provider: str
    model_name: str
    stages: dict[str, StageExecution]
    guardrails: GuardrailSummary
    cost: CostSummary
    artifacts: dict[str, str]  # tier → artifact path
```

#### Outputs

| Output | Location | Format |
|--------|----------|--------|
| JSON report | `data/reports/{run_id}.json` | Machine-readable |
| Markdown report | `data/reports/{run_id}.md` | Human-readable |

#### Report Contents

- **Metadata**: run_id, novel name, timestamps, duration
- **LLM Info**: provider, model name
- **Stage Execution**: chapters processed, arcs created, skipped flags
- **Guardrail Summary**: event counts by classification
- **Cost Summary**: total tokens, estimated cost
- **Artifact Paths**: locations of all generated files

---

## 5. Tier-2: Structural Features

### 5.1 Character Surface Index

**Source:** [character_indexing.py](../character_indexing.py)

#### Purpose

Extract surface-level name statistics from condensed text. Provide factual data for downstream Tier-3 analysis.

#### What This IS

- **Surface-level extraction**: Regex-based name detection
- **Statistical aggregation**: Mention counts, chapter presence
- **Structural data**: Co-occurrence within windows

#### What This IS NOT

- **NOT character identification**: Cannot distinguish "John" the farmer from "John" the merchant
- **NOT relationship inference**: Co-occurrence ≠ relationship
- **NOT narrative analysis**: No understanding of character roles

#### Name Detection Rules

1. **Capitalized words**: First letter uppercase, rest lowercase
2. **Multi-word names**: Title Case sequences (e.g., "Li Wei")
3. **Minimum threshold**: Single-word names require `MIN_SINGLE_WORD_MENTIONS=2`
4. **Exclusion list**: Common words filtered via `EXCLUDED_WORDS` (120+ terms)

#### Excluded Words Sample

```python
EXCLUDED_WORDS = frozenset([
    "the", "this", "that", "with", "from", "into",
    "chapter", "system", "status", "level", "skill",
    "cultivation", "breakthrough", "realm", "stage",
    # ... 120+ terms
])
```

#### Co-occurrence Calculation

```python
CO_OCCURRENCE_WINDOW = 3  # sentences

# For each sentence containing name A:
#   Check previous 3 and next 3 sentences for name B
#   If found, increment co_occurrence[A][B]
```

#### Output Schema

```json
{
  "novel_name": "Heaven Reincarnation",
  "run_id": "run_20251231_044311_bf2e5ace",
  "tier": "tier-2",
  "total_chapters": 10,
  "total_unique_names": 45,
  "names": {
    "Li Wei": {
      "mentions": 150,
      "chapters_present": ["chapter_001", "chapter_002", ...],
      "chapter_count": 10
    }
  },
  "co_occurrences": {
    "Li Wei|Zhang Chen": 25
  },
  "warnings": [
    "This is SURFACE-LEVEL extraction only",
    "Same name may refer to different characters",
    "Co-occurrence is textual proximity, NOT relationship"
  ]
}
```

#### Output Location

`data/character_index/{novel_name}/{run_id}.character_index.json`

---

## 6. Tier-3: Reader-Facing Intelligence

### 6.1 Character Salience

**Source:** [character_salience.py](../character_salience.py)

#### Purpose

Compute textual dominance scores from Tier-2 surface data. Measure how much each character name dominates the narrative surface.

#### What This IS

- **Textual dominance measurement**: Which names appear most prominently
- **Composite scoring**: Weighted combination of mention, coverage, persistence

#### What This IS NOT

- **NOT protagonist identification**: High salience ≠ protagonist
- **NOT importance ranking**: Salience is textual presence, not narrative importance
- **NOT role inference**: Cannot determine character function in story

#### Salience Formula

```
salience = (MENTION_WEIGHT × mention_score) +
           (COVERAGE_WEIGHT × coverage_score) +
           (PERSISTENCE_WEIGHT × persistence_score)
```

#### Component Formulas

**Mention Score (Weight: 0.5)**
```
raw_mention = character_mentions / max_mentions_any_character
mention_score = min(1.0, raw_mention)
```

**Coverage Score (Weight: 0.3)**
```
coverage_score = chapters_present / total_chapters
```

**Persistence Score (Weight: 0.2)**
```
# Measures how evenly distributed appearances are
# High persistence = appears throughout story
# Low persistence = clustered in specific sections

chapter_indices = [index for each chapter where character appears]
gaps = differences between consecutive indices
persistence_score = 1 - (gap_variance / max_possible_variance)
```

#### Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `MENTION_WEIGHT` | 0.5 | Weight for mention frequency |
| `COVERAGE_WEIGHT` | 0.3 | Weight for chapter coverage |
| `PERSISTENCE_WEIGHT` | 0.2 | Weight for distribution evenness |

#### Output Schema

```json
{
  "novel_name": "Heaven Reincarnation",
  "run_id": "run_20251231_044311_bf2e5ace",
  "tier": "tier-3.1",
  "source_tier2_run_id": "run_20251231_044311_bf2e5ace",
  "total_characters": 45,
  "characters": [
    {
      "name": "Li Wei",
      "mentions": 150,
      "chapter_count": 10,
      "mention_score": 1.0,
      "coverage_score": 1.0,
      "persistence_score": 0.95,
      "salience_score": 0.99
    }
  ],
  "warnings": [
    "Salience is TEXTUAL DOMINANCE, not narrative importance",
    "High salience does NOT identify protagonists"
  ]
}
```

#### Output Location

`data/character_salience/{novel_name}/{run_id}.character_salience.json`

---

### 6.2 Relationship Signal Matrix

**Source:** [relationship_matrix.py](../relationship_matrix.py)

#### Purpose

Compute structural co-presence signals between character pairs. Measure which characters persistently appear together across the narrative.

#### What This IS

- **Structural measurement**: Which pairs co-appear in same chapters
- **Persistence tracking**: How sustained is the co-presence
- **Signal extraction**: Raw data for downstream pattern detection

#### What This IS NOT

- **NOT relationship inference**: Co-presence ≠ relationship
- **NOT role detection**: Cannot determine if characters are allies, enemies, etc.
- **NOT semantic analysis**: Purely textual proximity

#### Signal Definitions

| Signal | Formula | Range | Interpretation |
|--------|---------|-------|----------------|
| `co_presence_count` | \|chapters_A ∩ chapters_B\| | [0, N] | Raw co-occurrence |
| `co_presence_ratio` | count / min(coverage_A, coverage_B) | [0, 1] | Normalized frequency |
| `jaccard_similarity` | \|A ∩ B\| / \|A ∪ B\| | [0, 1] | Set similarity |
| `narrative_span` | (last_co_chapter - first_co_chapter) / total | [0, 1] | Temporal spread |
| `persistence_score` | Weighted composite | [0, 1] | Sustained presence |

#### Persistence Formula

```python
persistence = (RATIO_WEIGHT × co_presence_ratio) +
              (SPAN_WEIGHT × narrative_span) +
              (DENSITY_WEIGHT × density_factor)

# Where density_factor = co_presence_count / span_chapters
```

#### Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `SALIENCE_THRESHOLD` | 0.1 | Minimum salience to include character |
| `MINIMUM_CO_PRESENCE` | 1 | Minimum co-occurrences for pair |
| `PERSISTENCE_RATIO_WEIGHT` | 0.4 | Weight in persistence formula |
| `PERSISTENCE_SPAN_WEIGHT` | 0.35 | Weight in persistence formula |
| `PERSISTENCE_DENSITY_WEIGHT` | 0.25 | Weight in persistence formula |

#### Output Schema

```json
{
  "novel_name": "Heaven Reincarnation",
  "run_id": "run_20251231_044311_bf2e5ace",
  "tier": "tier-3.2",
  "total_pairs": 120,
  "pairs": {
    "Li Wei|Zhang Chen": {
      "character_a": "Li Wei",
      "character_b": "Zhang Chen",
      "co_presence_count": 8,
      "co_presence_ratio": 0.80,
      "jaccard_similarity": 0.67,
      "narrative_span": 0.90,
      "persistence_score": 0.78
    }
  },
  "warnings": [
    "Co-presence is STRUCTURAL, not semantic",
    "High persistence does NOT indicate close relationships"
  ]
}
```

#### Output Location

`data/relationship_matrix/{novel_name}/{run_id}.relationship_matrix.json`

---

### 6.3 Event Keywords

**Source:** [event_keywords.py](../event_keywords.py)

#### Purpose

Scan condensed text for predefined event-related keywords. Extract lexical signals showing where event terms appear.

#### What This IS

- **Lexical scanning**: Pattern matching for predefined terms
- **Distribution tracking**: Where keywords appear across chapters
- **Signal extraction**: Raw data for genre/tag detection

#### What This IS NOT

- **NOT event detection**: Keyword presence ≠ event occurrence
- **NOT semantic analysis**: Cannot confirm narrative meaning
- **NOT interpretation**: Reports signals, not conclusions

#### Keyword Dictionary

**Version:** 1.0.0

| Category | Keywords |
|----------|----------|
| `transmigration` | reincarnation, transmigration, regression, second_chance, possession |
| `system` | system_awakening, level_up, skill_acquisition, quest, status_window |
| `cultivation` | breakthrough, tribulation, enlightenment, realm_advancement |
| `conflict` | battle, death, revenge, betrayal |
| `discovery` | treasure, inheritance, secret, awakening |
| `world_event` | apocalypse, war, tournament, catastrophe |
| `transformation` | transformation, possession, resurrection |

#### Keyword Entry Format

```python
{
    "keyword_id": "reincarnation",
    "category": "transmigration",
    "terms": ["reincarnated", "reborn", "past life", "previous life"],
    "case_sensitive": False
}
```

#### Signal Schema

```python
@dataclass
class KeywordSignal:
    keyword_id: str
    category: str
    chapters_found: list[str]      # Which chapters contain term
    total_matches: int             # Total occurrences
    narrative_spread: int          # Number of unique chapters
    first_appearance: str          # First chapter
    last_appearance: str           # Last chapter
    density: float                 # matches / chapters_found
```

#### Output Schema

```json
{
  "novel_name": "Heaven Reincarnation",
  "run_id": "run_20251231_044311_bf2e5ace",
  "tier": "tier-3.3",
  "dictionary_version": "1.0.0",
  "keywords": {
    "reincarnation": {
      "keyword_id": "reincarnation",
      "category": "transmigration",
      "chapters_found": ["chapter_001", "chapter_002"],
      "total_matches": 15,
      "narrative_spread": 2,
      "density": 7.5
    }
  },
  "categories_found": {
    "transmigration": ["reincarnation", "second_chance"],
    "cultivation": ["breakthrough", "tribulation"]
  },
  "warnings": [
    "Keyword presence does NOT confirm event occurred",
    "This is LEXICAL data, not narrative analysis"
  ]
}
```

#### Output Location

`data/event_keywords/{novel_name}/{run_id}.event_keywords.json`

---

### 6.4 Genre Resolver

**Source:** [genre_resolver.py](../genre_resolver.py)

#### Purpose

Resolve genre signals from upstream Tier-3 data using deterministic, rule-based evaluation.

#### What This IS

- **Rule-based evaluation**: Explicit, documented rules
- **Evidence aggregation**: Combines Tier-3.1, 3.2, 3.3 signals
- **Multi-genre output**: Multiple genres can have high confidence

#### What This IS NOT

- **NOT LLM-based**: No semantic similarity or text generation
- **NOT interpretive**: Does not understand story meaning
- **NOT single-label**: Does not force one "best" genre

#### Genre Taxonomy

**Version:** 1.0.0  
**Source:** Feydar/novelupdates_genre

| Genre ID | Display Name | Required Evidence |
|----------|--------------|-------------------|
| `xianxia` | Xianxia | `cultivation` category present |
| `xuanhuan` | Xuanhuan | `cultivation` category present |
| `wuxia` | Wuxia | `conflict` category present |
| `isekai` | Isekai | `transmigration` category present |
| `reincarnation` | Reincarnation | `reincarnation` keyword present |
| `system` | System | `system` category present |
| `litrpg` | LitRPG | `system` category present |
| `action` | Action | `conflict` category present |
| `adventure` | Adventure | `discovery` category present |
| `fantasy` | Fantasy | (evidence-based, no hard gate) |
| `drama` | Drama | (evidence-based, no hard gate) |
| `tragedy` | Tragedy | `death` keyword present |
| `mystery` | Mystery | `secret` keyword present |
| `horror` | Horror | `conflict` category present |
| `harem` | Harem | (evidence-based, no hard gate) |
| `supernatural` | Supernatural | (evidence-based, no hard gate) |

#### Rule Model

```python
GENRE_RULES = {
    "xianxia": {
        "base_score": 0.5,
        "required": {
            "category_present": ["cultivation"],
        },
        "boosts": [
            ("keyword_present", "tribulation", 0.15),
            ("keyword_present", "enlightenment", 0.10),
            ("keyword_spread", ("breakthrough", 3), 0.10),
        ],
        "penalties": [
            ("category_present", "system", 0.10),
        ],
    },
}
```

#### Confidence Formula

```
confidence = base_score + sum(boosts) - sum(penalties)
confidence = clamp(confidence, 0.0, 1.0)
```

#### Condition Types

| Condition | Parameters | Description |
|-----------|------------|-------------|
| `keyword_present` | keyword_id | Keyword exists in event keywords |
| `category_present` | category | Category exists in event keywords |
| `keyword_spread` | (keyword_id, min_spread) | Keyword narrative_spread >= value |
| `keyword_density` | (keyword_id, min_density) | Keyword density >= value |
| `category_count` | (category, min_count) | Category has >= N keywords |
| `salient_character_count` | (count, min_salience) | >= N characters with salience >= value |
| `salient_pair_persistence` | min_persistence | Any pair has persistence >= value |
| `high_persistence_pair_count` | (count, min_persistence) | >= N pairs with persistence >= value |

#### Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `CONFIDENCE_THRESHOLD` | 0.3 | Minimum confidence for output inclusion |
| `GENRE_TAXONOMY_VERSION` | "1.0.0" | Taxonomy version |
| `GENRE_RULE_VERSION` | "1.0.0" | Rule logic version |

#### Output Location

`data/genre_resolved/{novel_name}/{run_id}.genre_resolved.json`

---

### 6.5 Tag Resolver

**Source:** [tag_resolver.py](../tag_resolver.py)

#### Purpose

Resolve tag signals from upstream Tier-3 data using deterministic, rule-based evaluation. Tags provide granular narrative descriptors beyond genre classification.

#### What This IS

- **Rule-based evaluation**: Explicit, documented rules
- **Evidence aggregation**: Combines Tier-3.1, 3.2, 3.3, 3.4a signals
- **Multi-tag output**: Multiple tags can have high confidence

#### What This IS NOT

- **NOT LLM-based**: No semantic similarity or text generation
- **NOT interpretive**: Does not understand story meaning
- **NOT subjective**: Only tags with detectable evidence

#### Tag Taxonomy (Partial)

**Version:** 1.0.0  
**Source:** Feydar/novelupdates_tags (curated)

| Tag ID | Display Name | Primary Evidence |
|--------|--------------|------------------|
| `reincarnation` | Reincarnation | `reincarnation` keyword |
| `cultivation` | Cultivation | `cultivation` category |
| `overpowered_protagonist` | Overpowered Protagonist | Battle spread + system genre |
| `betrayal` | Betrayal | `betrayal` keyword |
| `marriage` | Marriage | High persistence pairs + romance genre |
| `polygamy` | Polygamy | Multiple high-persistence pairs |
| `multiple_protagonists` | Multiple Protagonists | Multiple high-salience characters |
| `age_regression` | Age Regression | `regression` keyword |
| `body_swap` | Body Swap | `possession` keyword |
| `transformation_ability` | Transformation Ability | `transformation` category |
| `ancient_china` | Ancient China | Xianxia/wuxia genre |

#### Additional Condition Types

Beyond genre resolver conditions:

| Condition | Parameters | Description |
|-----------|------------|-------------|
| `genre_present` | genre_id | Genre resolved with confidence >= threshold |
| `genre_confidence` | (genre_id, min_confidence) | Genre confidence >= specific value |

#### Tag Rule Example

```python
TAG_RULES = {
    "overpowered_protagonist": {
        "base_score": 0.3,
        "required": {},  # Evidence-based, no hard gate
        "boosts": [
            ("keyword_spread", ("battle", 4), 0.20),
            ("genre_present", "system", 0.15),
            ("genre_present", "xianxia", 0.10),
            ("keyword_spread", ("breakthrough", 4), 0.15),
        ],
        "penalties": [
            ("keyword_spread", ("death", 3), 0.15),
        ],
    },
}
```

#### Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `CONFIDENCE_THRESHOLD` | 0.3 | Minimum confidence for output inclusion |
| `TAG_TAXONOMY_VERSION` | "1.0.0" | Taxonomy version |
| `TAG_RULE_VERSION` | "1.0.0" | Rule logic version |

#### Output Location

`data/tag_resolved/{novel_name}/{run_id}.tag_resolved.json`

---

## 7. Utilities

**Source:** [utils.py](../utils.py)

### estimate_tokens()

Estimate token count for text without calling tokenizer API.

```python
def estimate_tokens(text: str) -> int:
    """
    Rough estimation: ~4 characters per token for English.
    Adjusts for CJK characters (~1.5 chars per token).
    """
    # Simplified: return len(text) // 4
```

### reduce_until_fit()

Recursively reduce text until it fits within token limit.

```python
def reduce_until_fit(
    text: str,
    max_tokens: int,
    condense_fn: Callable[[str], str],
    resume_state: Optional[dict] = None,
) -> str:
    """
    If text exceeds max_tokens:
    1. Split into halves
    2. Recursively reduce each half
    3. Combine and reduce again
    
    Resume support: Can continue from partial state on failure.
    """
```

---

## 8. Artifact Reference

### Quick Reference Table

| Tier | Feature | Artifact Path | Format |
|------|---------|---------------|--------|
| Core | Chapters | `data/chapters_condensed/{novel}/{chapter}.condensed.txt` | Text |
| Core | Arcs | `data/arcs_condensed/{novel}/arc_{n}.condensed.txt` | Text |
| Core | Novel | `data/novel_condensed/{novel}/novel.condensed.txt` | Text |
| 1 | Reports | `data/reports/{run_id}.json`, `{run_id}.md` | JSON, Markdown |
| 2 | Character Index | `data/character_index/{novel}/{run_id}.character_index.json` | JSON |
| 3.1 | Salience | `data/character_salience/{novel}/{run_id}.character_salience.json` | JSON |
| 3.2 | Relationships | `data/relationship_matrix/{novel}/{run_id}.relationship_matrix.json` | JSON |
| 3.3 | Keywords | `data/event_keywords/{novel}/{run_id}.event_keywords.json` | JSON |
| 3.4a | Genre | `data/genre_resolved/{novel}/{run_id}.genre_resolved.json` | JSON |
| 3.4b | Tags | `data/tag_resolved/{novel}/{run_id}.tag_resolved.json` | JSON |

### Version Tracking

| Artifact | Version Field | Current |
|----------|---------------|---------|
| Event Keywords | `dictionary_version` | 1.0.0 |
| Genre | `taxonomy_version`, `rule_version` | 1.0.0, 1.0.0 |
| Tags | `taxonomy_version`, `rule_version` | 1.0.0, 1.0.0 |

---

## 9. LLM Provider Configuration

**Source:** [llm/llm_config.py](../llm/llm_config.py)

### Supported Providers

| Provider | Env Var | Models |
|----------|---------|--------|
| Gemini | `GEMINI_API_KEY` | gemini-2.0-flash-exp, gemini-1.5-flash |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| Groq | `GROQ_API_KEY` | llama-3.3-70b-versatile |
| Cerebras | `CEREBRAS_API_KEY` | llama-3.3-70b |
| Copilot | (VS Code integration) | gpt-4 |
| Ollama | `OLLAMA_HOST` | (local models) |
| vLLM | `VLLM_BASE_URL` | (custom endpoint) |

### Provider Selection

```bash
export LLM_PROVIDER=gemini  # or deepseek, groq, etc.
export GEMINI_API_KEY=your_key_here
```

### Retry Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_LLM_RETRIES` | 3 | Maximum retry attempts on failure |

---

## 10. CLI Reference

### run_pipeline.py

```bash
python run_pipeline.py <novel_name> [OPTIONS]
```

#### Core Options

| Option | Description |
|--------|-------------|
| `--skip-chapters` | Reuse existing condensed chapters |
| `--skip-arcs` | Reuse existing condensed arcs |
| `--skip-novel` | Reuse existing novel condensation |

#### Tier-2 Options

| Option | Description |
|--------|-------------|
| `--character-index` | Generate character surface index |

#### Tier-3 Options

| Option | Description |
|--------|-------------|
| `--character-salience` | Compute character salience scores |
| `--relationship-matrix` | Compute character pair co-presence signals |
| `--event-keywords` | Scan for event keyword signals |
| `--genre-resolver` | Resolve genres from Tier-3 evidence |
| `--tag-resolver` | Resolve tags from Tier-3 evidence |

### Example Invocations

```bash
# Full pipeline run
python run_pipeline.py "Heaven Reincarnation"

# Skip condensation, run all analysis features
python run_pipeline.py "Heaven Reincarnation" \
    --skip-chapters --skip-arcs --skip-novel \
    --character-index \
    --character-salience \
    --relationship-matrix \
    --event-keywords \
    --genre-resolver \
    --tag-resolver

# Only chapters + character index
python run_pipeline.py "Heaven Reincarnation" \
    --skip-arcs --skip-novel \
    --character-index
```

---

## Consumer Warnings (Global)

All downstream consumers of Abridge artifacts MUST understand:

1. **Confidence ≠ Probability**: Scores reflect evidence strength, not statistical likelihood
2. **Multi-label is expected**: Multiple genres/tags can have high confidence
3. **Low confidence ≠ Absence**: Insufficient evidence, not definitive exclusion
4. **Surface-level only**: All features measure textual presence, not narrative meaning
5. **Deterministic but LLM-dependent**: Same input → same tier output (given same LLM responses)
6. **Audit trail exists**: All operations are logged for post-run analysis

---

*End of Documentation*
