"""
prefilter.py - Deterministic Pre-Filtering for Chapter Condensation

PURPOSE:
    Remove non-plot text BEFORE LLM condensation to reduce token costs and noise.
    This is a STRUCTURAL operation that does not interpret narrative meaning.

FILTERING RULES (from TODO):
    A paragraph is KEPT if it has AT LEAST ONE of:
    1. Named entities (PERSON, ORG, GPE, LOC, FAC, EVENT, WORK_OF_ART, PRODUCT)
    2. Dialogue (text within quotation marks)
    3. Past-tense verbs (VBD tag from POS tagger)

    A paragraph is DROPPED only if it has NONE of the above.

LANGUAGE-AWARE RULE (CRITICAL):
    spaCy-based filtering is ONLY applied to English text.
    
    IF input_language == "en":
        spaCy MAY: annotate, filter paragraphs, support deletion rules
    ELSE:
        spaCy MAY ONLY: annotate, segment, collect hints
        spaCy MUST NOT: delete paragraphs, gate content, decide plot relevance
    
    Rationale: The en_core_web_sm model is trained on English. Applying it to
    Chinese, Japanese, or other languages would produce unreliable NER/POS tags,
    leading to incorrect paragraph drops and plot loss.

DESIGN PRINCIPLES:
    - Deterministic: Same input always produces same output
    - Conservative: When in doubt, KEEP the paragraph
    - Non-semantic: Rules are lexical/syntactic, not interpretive
    - Transparent: Filtering decisions can be logged and audited
    - Language-safe: Non-English text passes through unchanged

NON-GOALS:
    - This module does NOT judge importance
    - This module does NOT reorder content
    - This module does NOT merge paragraphs
    - This module does NOT interpret themes or meaning

DEPENDENCIES:
    - spaCy with 'en_core_web_sm' model for NER and POS tagging
    - re (standard library) for dialogue detection
"""

import re
from dataclasses import dataclass
from typing import Optional

# Lazy-load spaCy to avoid import overhead when not needed
_nlp = None


def _get_nlp():
    """Lazy-load spaCy model. Downloads if not present."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            try:
                _nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Model not installed - download it
                print("[prefilter] Downloading spaCy model 'en_core_web_sm'...")
                import subprocess
                subprocess.run(
                    ["python", "-m", "spacy", "download", "en_core_web_sm"],
                    check=True,
                    capture_output=True,
                )
                _nlp = spacy.load("en_core_web_sm")
        except ImportError:
            raise ImportError(
                "spaCy is required for pre-filtering. "
                "Install with: pip install spacy"
            )
    return _nlp


# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Entity types that indicate plot-relevant content
# These are conservative: any named entity suggests the paragraph may matter
PLOT_RELEVANT_ENTITY_TYPES = {
    "PERSON",       # People, including fictional
    "ORG",          # Organizations
    "GPE",          # Geo-political entities (countries, cities)
    "LOC",          # Non-GPE locations (mountains, rivers)
    "FAC",          # Facilities (buildings, airports)
    "EVENT",        # Named events
    "WORK_OF_ART",  # Titles of works
    "PRODUCT",      # Products, objects
    "NORP",         # Nationalities, religious, political groups
}

# Regex patterns for dialogue detection
# Matches both single and double quotes, including various Unicode quotation marks
DIALOGUE_PATTERNS = [
    r'"[^"]+?"',           # Double quotes (straight)
    r"'[^']+?'",           # Single quotes (straight)
    r'"[^"]+?"',           # Double quotes (curly)
    r"'[^']+?'",           # Single quotes (curly) - using raw string escape
    r'「[^」]+?」',         # CJK quotation marks
    r'『[^』]+?』',         # CJK double quotation marks
    r'«[^»]+?»',           # Guillemets
]

# Compiled dialogue regex (any of the patterns)
DIALOGUE_REGEX = re.compile("|".join(DIALOGUE_PATTERNS))


# --------------------------------------------------
# Language Detection
# --------------------------------------------------

def _detect_language(text: str) -> str:
    """
    Detect the primary language of the text.
    
    Uses a simple heuristic based on character ranges:
    - If significant CJK characters are present, assume non-English
    - Otherwise, assume English
    
    This is a conservative check: we err on the side of detecting
    non-English to avoid incorrect filtering.
    
    Returns:
        "en" for English, "non-en" for any other language
    """
    if not text:
        return "en"
    
    # Count characters by type
    cjk_count = 0
    latin_count = 0
    
    for char in text:
        code = ord(char)
        # CJK Unified Ideographs and common CJK ranges
        if (0x4E00 <= code <= 0x9FFF or    # CJK Unified Ideographs
            0x3400 <= code <= 0x4DBF or    # CJK Extension A
            0x3000 <= code <= 0x303F or    # CJK Punctuation
            0x3040 <= code <= 0x309F or    # Hiragana
            0x30A0 <= code <= 0x30FF or    # Katakana
            0xAC00 <= code <= 0xD7AF):     # Korean Hangul
            cjk_count += 1
        elif (0x0041 <= code <= 0x005A or  # A-Z
              0x0061 <= code <= 0x007A):   # a-z
            latin_count += 1
    
    # If more than 10% of alphabetic characters are CJK, treat as non-English
    total_alpha = cjk_count + latin_count
    if total_alpha > 0 and cjk_count / total_alpha > 0.1:
        return "non-en"
    
    return "en"


# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class ParagraphAnalysis:
    """Analysis result for a single paragraph."""
    text: str
    has_named_entity: bool
    has_dialogue: bool
    has_past_tense_verb: bool
    keep: bool
    
    @property
    def reason(self) -> str:
        """Human-readable reason for keep/drop decision."""
        if not self.keep:
            return "no named entities, no dialogue, no past-tense verbs"
        reasons = []
        if self.has_named_entity:
            reasons.append("named entity")
        if self.has_dialogue:
            reasons.append("dialogue")
        if self.has_past_tense_verb:
            reasons.append("past-tense verb")
        return ", ".join(reasons)


@dataclass
class PrefilterResult:
    """Result of pre-filtering a chapter."""
    original_text: str
    filtered_text: str
    original_paragraph_count: int
    kept_paragraph_count: int
    dropped_paragraph_count: int
    paragraphs: list[ParagraphAnalysis]
    detected_language: str = "en"  # "en" or "non-en"
    filtering_applied: bool = True  # False if skipped due to non-English
    
    @property
    def drop_ratio(self) -> float:
        """Ratio of dropped paragraphs (0.0 to 1.0)."""
        if self.original_paragraph_count == 0:
            return 0.0
        return self.dropped_paragraph_count / self.original_paragraph_count


# --------------------------------------------------
# Detection Functions
# --------------------------------------------------

def _has_dialogue(text: str) -> bool:
    """
    Check if text contains dialogue (quoted speech).
    
    Uses regex to detect various quotation mark styles.
    This is a conservative check - false positives are acceptable.
    """
    return bool(DIALOGUE_REGEX.search(text))


def _has_named_entity(doc) -> bool:
    """
    Check if spaCy doc contains plot-relevant named entities.
    
    Args:
        doc: spaCy Doc object (already processed)
    
    Returns:
        True if any named entity of a relevant type is found.
    """
    for ent in doc.ents:
        if ent.label_ in PLOT_RELEVANT_ENTITY_TYPES:
            return True
    return False


def _has_past_tense_verb(doc) -> bool:
    """
    Check if spaCy doc contains past-tense verbs.
    
    Past-tense verbs (VBD tag) typically indicate actions and events.
    This is a proxy for "something happened" in the paragraph.
    
    Args:
        doc: spaCy Doc object (already processed)
    
    Returns:
        True if any past-tense verb is found.
    """
    for token in doc:
        if token.tag_ == "VBD":  # Verb, past tense
            return True
    return False


# --------------------------------------------------
# Core Pre-Filtering Logic
# --------------------------------------------------

def analyze_paragraph(text: str, nlp=None) -> ParagraphAnalysis:
    """
    Analyze a single paragraph for plot-relevance signals.
    
    Args:
        text: The paragraph text to analyze.
        nlp: Optional spaCy model. If None, will lazy-load.
    
    Returns:
        ParagraphAnalysis with detection results and keep/drop decision.
    """
    if nlp is None:
        nlp = _get_nlp()
    
    # Skip empty or whitespace-only paragraphs
    stripped = text.strip()
    if not stripped:
        return ParagraphAnalysis(
            text=text,
            has_named_entity=False,
            has_dialogue=False,
            has_past_tense_verb=False,
            keep=False,
        )
    
    # Check for dialogue first (fast regex check)
    has_dialogue = _has_dialogue(stripped)
    
    # Process with spaCy for NER and POS
    doc = nlp(stripped)
    has_named_entity = _has_named_entity(doc)
    has_past_tense_verb = _has_past_tense_verb(doc)
    
    # KEEP if ANY of the three signals is present
    keep = has_named_entity or has_dialogue or has_past_tense_verb
    
    return ParagraphAnalysis(
        text=text,
        has_named_entity=has_named_entity,
        has_dialogue=has_dialogue,
        has_past_tense_verb=has_past_tense_verb,
        keep=keep,
    )


def prefilter_chapter(chapter_text: str, verbose: bool = False) -> PrefilterResult:
    """
    Apply deterministic pre-filtering to a chapter.
    
    LANGUAGE-AWARE: Filtering is ONLY applied to English text.
    Non-English text (Chinese, Japanese, Korean, etc.) passes through unchanged.
    
    Splits text into paragraphs (by blank lines), analyzes each,
    and removes paragraphs that have no plot-relevant signals.
    
    Args:
        chapter_text: The raw chapter text.
        verbose: If True, print analysis for each paragraph.
    
    Returns:
        PrefilterResult with filtered text and analysis details.
    """
    # LANGUAGE CHECK: Only filter English text
    detected_lang = _detect_language(chapter_text)
    
    if detected_lang != "en":
        # NON-ENGLISH: Return original text unchanged
        # spaCy MUST NOT delete paragraphs for non-English text
        if verbose:
            print(f"  [SKIP] Non-English text detected - filtering disabled")
        
        paragraphs = re.split(r'\n\s*\n', chapter_text)
        # Create placeholder analyses (all kept)
        analyses = [
            ParagraphAnalysis(
                text=para,
                has_named_entity=False,  # Not analyzed
                has_dialogue=False,      # Not analyzed
                has_past_tense_verb=False,  # Not analyzed
                keep=True,  # Always keep for non-English
            )
            for para in paragraphs
        ]
        
        return PrefilterResult(
            original_text=chapter_text,
            filtered_text=chapter_text,  # Unchanged
            original_paragraph_count=len(paragraphs),
            kept_paragraph_count=len(paragraphs),
            dropped_paragraph_count=0,
            paragraphs=analyses,
            detected_language=detected_lang,
            filtering_applied=False,
        )
    
    # ENGLISH: Apply full filtering
    nlp = _get_nlp()
    
    # Split into paragraphs by one or more blank lines
    # Preserve paragraph structure for reconstruction
    paragraphs = re.split(r'\n\s*\n', chapter_text)
    
    analyses = []
    kept_paragraphs = []
    
    for para in paragraphs:
        analysis = analyze_paragraph(para, nlp)
        analyses.append(analysis)
        
        if analysis.keep:
            kept_paragraphs.append(para)
            if verbose:
                preview = para[:50].replace('\n', ' ') + "..." if len(para) > 50 else para.replace('\n', ' ')
                print(f"  [KEEP] ({analysis.reason}): {preview}")
        else:
            if verbose:
                preview = para[:50].replace('\n', ' ') + "..." if len(para) > 50 else para.replace('\n', ' ')
                print(f"  [DROP] ({analysis.reason}): {preview}")
    
    # Reconstruct text with kept paragraphs
    filtered_text = "\n\n".join(kept_paragraphs)
    
    original_count = len(paragraphs)
    kept_count = len(kept_paragraphs)
    dropped_count = original_count - kept_count
    
    return PrefilterResult(
        original_text=chapter_text,
        filtered_text=filtered_text,
        original_paragraph_count=original_count,
        kept_paragraph_count=kept_count,
        dropped_paragraph_count=dropped_count,
        paragraphs=analyses,
        detected_language=detected_lang,
        filtering_applied=True,
    )


# --------------------------------------------------
# Convenience Functions
# --------------------------------------------------

def prefilter_text(text: str) -> str:
    """
    Simple interface: return filtered text only.
    
    Args:
        text: Raw chapter text.
    
    Returns:
        Filtered text with non-plot paragraphs removed.
    """
    result = prefilter_chapter(text)
    return result.filtered_text


def get_prefilter_stats(text: str) -> dict:
    """
    Get statistics about pre-filtering without returning filtered text.
    
    Useful for logging and monitoring.
    
    Args:
        text: Raw chapter text.
    
    Returns:
        Dictionary with paragraph counts and ratios.
    """
    result = prefilter_chapter(text)
    return {
        "original_paragraphs": result.original_paragraph_count,
        "kept_paragraphs": result.kept_paragraph_count,
        "dropped_paragraphs": result.dropped_paragraph_count,
        "drop_ratio": result.drop_ratio,
    }


# --------------------------------------------------
# Module Self-Test
# --------------------------------------------------

if __name__ == "__main__":
    # Simple test with sample text
    test_text = """
Chapter 1: The Beginning

In a mysterious space of endless darkness.

A transparent and illusory small light sphere was quietly floating there.

"So... I'm already dead!" Zhao Gao thought to himself.

His heart was full of questions about it.

The sky was blue. The grass was green.

Zhao Gao walked towards the distant mountains.

He barely hesitated, immediately stood up from the ground.
"""
    
    print("=== Pre-Filter Test ===\n")
    result = prefilter_chapter(test_text, verbose=True)
    
    print(f"\n=== Statistics ===")
    print(f"Detected language: {result.detected_language}")
    print(f"Filtering applied: {result.filtering_applied}")
    print(f"Original paragraphs: {result.original_paragraph_count}")
    print(f"Kept paragraphs: {result.kept_paragraph_count}")
    print(f"Dropped paragraphs: {result.dropped_paragraph_count}")
    print(f"Drop ratio: {result.drop_ratio:.1%}")
    
    print(f"\n=== Filtered Text ===")
    print(result.filtered_text)
    
    # Test with Chinese text (should NOT be filtered)
    chinese_text = """
第一章：天道轮回系统

在一片无尽黑暗的神秘空间中。

一颗透明虚幻的小光球静静地漂浮在那里。

"所以……我已经死了！"赵高心想。

他的心中充满了疑问。

天空是蓝色的。草是绿色的。

赵高向远处的群山走去。
"""
    
    print("\n\n=== Chinese Text Test (should NOT filter) ===\n")
    result_cn = prefilter_chapter(chinese_text, verbose=True)
    
    print(f"\n=== Statistics ===")
    print(f"Detected language: {result_cn.detected_language}")
    print(f"Filtering applied: {result_cn.filtering_applied}")
    print(f"Original paragraphs: {result_cn.original_paragraph_count}")
    print(f"Kept paragraphs: {result_cn.kept_paragraph_count}")
    print(f"Dropped paragraphs: {result_cn.dropped_paragraph_count}")
    print(f"Drop ratio: {result_cn.drop_ratio:.1%}")
