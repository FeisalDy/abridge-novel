import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------

CHARACTER_PROFILES_DIR = os.getenv("ABRIDGE_CHARACTER_PROFILES_DIR", "data/character_profiles")
CHARACTER_SALIENCE_DIR = os.getenv("ABRIDGE_CHARACTER_SALIENCE_DIR", "data/character_salience")
RELATIONSHIP_MATRIX_DIR = os.getenv("ABRIDGE_RELATIONSHIP_MATRIX_DIR", "data/relationship_matrix")
EVENT_KEYWORDS_DIR = os.getenv("ABRIDGE_EVENT_KEYWORDS_DIR", "data/event_keywords")

# Profile version aligned with Dictionary v1.0.2
PROFILER_VERSION = "1.1.0"

PROTAGONIST_SALIENCE_THRESHOLD = 0.3
SUPPORTING_SALIENCE_THRESHOLD = 0.15
ROMANTIC_PERSISTENCE_THRESHOLD = 0.5
EARLY_STORY_PERCENTAGE = 0.10

# --------------------------------------------------
# CATEGORY MAPPING (Aligned with Upstream v1.0.2)
# --------------------------------------------------

MALE_CATEGORIES = {"gender_indicator_male", "sect_leadership_male"}
FEMALE_CATEGORIES = {"gender_indicator_female", "jade_beauty_signals"}

# Origin mapping
ORIGIN_EVENT_CATEGORIES = {"origin_event"}
MODERN_ERA_CATEGORIES = {"origin_modern"}
ANCIENT_ERA_CATEGORIES = {"setting_ancient_china", "cultivation_society"}

# Power System mapping
QI_ENERGY_CATEGORIES = {"cultivation_realm", "cultivation_society"}
INTERNAL_ENERGY_CATEGORIES = {"power_system_wuxia"}
MANA_ENERGY_CATEGORIES = {"power_system_western"}
GAME_SYSTEM_CATEGORIES = {"power_system_game"}

# Social/Species mapping
ROMANCE_CATEGORIES = {"social_romance", "social_marriage", "social_harem"}
BEAST_CATEGORIES = {"morphology_change"}


# --------------------------------------------------
# Data Structures
# --------------------------------------------------

@dataclass
class CharacterIdentity:
    """Identity attributes for a character."""
    inferred_gender: str = "unknown"
    original_gender: str = "unknown"
    gender_changed: bool = False
    species: str = "unknown"
    is_humanoid: bool = True


@dataclass
class CharacterOriginState:
    """Origin/transmigration state for a character."""
    type: str = "unknown"  # native/transmigration/reincarnation/regression
    era: str = "unknown"   # modern/ancient
    origin_evidence: list = field(default_factory=list)


@dataclass
class CharacterPowerSystem:
    """Power system attributes for a character."""
    energy_type: str = "unknown"  # qi/mana/internal
    attained_immortality: bool = False
    progression_style: str = "unknown"  # cultivation/level-based
    immortality_evidence: list = field(default_factory=list)


@dataclass
class CharacterSocial:
    """Social attributes for a character."""
    romantic_cardinality: int = 0
    harem_type: str = "none"
    social_class: str = "unknown"
    romantic_partners: list = field(default_factory=list)


@dataclass
class CharacterEvidenceSummary:
    """Evidence summary for transparency."""
    gendered_keywords: dict = field(default_factory=dict)
    origin_keywords: list = field(default_factory=list)
    power_keywords: list = field(default_factory=list)
    early_story_keywords: list = field(default_factory=list)
    late_story_keywords: list = field(default_factory=list)


@dataclass
class CharacterProfile:
    """Complete profile for a single character."""
    character_name: str
    role: str = "minor"
    salience_score: float = 0.0
    identity: CharacterIdentity = field(default_factory=CharacterIdentity)
    origin_state: CharacterOriginState = field(default_factory=CharacterOriginState)
    power_system: CharacterPowerSystem = field(default_factory=CharacterPowerSystem)
    social: CharacterSocial = field(default_factory=CharacterSocial)
    evidence_summary: CharacterEvidenceSummary = field(default_factory=CharacterEvidenceSummary)


@dataclass
class CharacterProfilesMap:
    """Complete character profiles output for a novel."""
    novel_name: str
    run_id: str
    tier: str = "tier-3.3.5"
    profiler_version: str = PROFILER_VERSION
    total_chapters: int = 0
    total_characters_profiled: int = 0
    protagonist_count: int = 0
    supporting_count: int = 0
    profiles: dict = field(default_factory=dict)
    input_artifacts: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


# --------------------------------------------------
# Artifact Loading
# --------------------------------------------------

def _load_artifact(directory: str, novel_name: str, run_id: str, suffix: str) -> Optional[dict]:
    path = os.path.join(directory, novel_name, f"{run_id}.{suffix}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    
    novel_dir = os.path.join(directory, novel_name)
    if not os.path.exists(novel_dir): return None
    artifacts = sorted([f for f in os.listdir(novel_dir) if f.endswith(f".{suffix}.json")], reverse=True)
    if artifacts:
        with open(os.path.join(novel_dir, artifacts[0]), "r", encoding="utf-8") as f: return json.load(f)
    return None

def _load_character_salience(n, r): return _load_artifact(CHARACTER_SALIENCE_DIR, n, r, "character_salience")
def _load_relationship_matrix(n, r): return _load_artifact(RELATIONSHIP_MATRIX_DIR, n, r, "relationship_matrix")
def _load_event_keywords(n, r): return _load_artifact(EVENT_KEYWORDS_DIR, n, r, "event_keywords")


# --------------------------------------------------
# Character State Profiler Engine
# --------------------------------------------------

class CharacterStateProfiler:
    """
    Deterministic rule-based engine for character state profiling.
    Uses category mapping from Tier-3.3 for high-precision inference.
    """

    def __init__(
        self,
        character_salience: Optional[dict],
        relationship_matrix: Optional[dict],
        event_keywords: Optional[dict],
    ):
        self.character_salience = character_salience or {}
        self.relationship_matrix = relationship_matrix or {}
        self.event_keywords = event_keywords or {}

        self._characters = self.character_salience.get("characters", [])
        self._pairs = self.relationship_matrix.get("pairs", {})
        self._keywords = self.event_keywords.get("keywords", {})
        self._total_chapters = self.event_keywords.get("total_chapters", 0)
        self._early_story_threshold = int(self._total_chapters * EARLY_STORY_PERCENTAGE)
        
        # Build keyword-to-actor map
        self._char_kw_map = {}
        for kw_id, kw_data in self._keywords.items():
            for name, count in kw_data.get("associated_characters", {}).items():
                if name not in self._char_kw_map: self._char_kw_map[name] = {}
                self._char_kw_map[name][kw_id] = count

    def _classify_role(self, salience_score: float) -> str:
        if salience_score >= PROTAGONIST_SALIENCE_THRESHOLD: return "protagonist"
        if salience_score >= SUPPORTING_SALIENCE_THRESHOLD: return "supporting"
        return "minor"

    def _infer_gender(self, name):
        male, female = 0, 0
        early_male, early_female = 0, 0

        for kw_id, count in self._char_kw_map.get(name, {}).items():
            kw = self._keywords[kw_id]
            cat = kw.get("category")
            first = kw.get("first_seen_unit", -1)

            if cat in MALE_CATEGORIES:
                male += count
                if first <= self._early_story_threshold: early_male += count
            elif cat in FEMALE_CATEGORIES:
                female += count
                if first <= self._early_story_threshold: early_female += count

        inf = "male" if male > female * 1.2 else "female" if female > male * 1.2 else "ambiguous"
        orig = "male" if early_male > early_female * 1.2 else "female" if early_female > early_male * 1.2 else inf
        return inf, orig, (inf != orig), {"male": male, "female": female}

    def _detect_origin(self, name):
        type_val, era = "native", "unknown"
        evidence, modern, ancient = [], 0, 0

        for kw_id, count in self._char_kw_map.get(name, {}).items():
            kw = self._keywords[kw_id]
            cat = kw.get("category")
            first = kw.get("first_seen_unit", -1)
            is_early = first >= 0 and first <= self._early_story_threshold

            if cat in ORIGIN_EVENT_CATEGORIES and is_early:
                kw_id_low = kw_id.lower()
                if "transmigra" in kw_id_low or "isekai" in kw_id_low: type_val = "transmigration"
                elif "reincarna" in kw_id_low or "reborn" in kw_id_low: type_val = "reincarnation"
                elif "regress" in kw_id_low or "return" in kw_id_low: type_val = "regression"
                evidence.append(kw_id)
            
            if cat in MODERN_ERA_CATEGORIES: modern += count
            elif cat in ANCIENT_ERA_CATEGORIES: ancient += count

        era = "modern" if modern > ancient else "ancient" if ancient > 0 else "unknown"
        return type_val, era, evidence

    def _detect_power_system(self, name):
        energy, style = "unknown", "unknown"
        immortal = False
        imm_evidence = []
        counts = {"qi": 0, "internal": 0, "mana": 0}

        for kw_id, count in self._char_kw_map.get(name, {}).items():
            kw = self._keywords[kw_id]
            cat = kw.get("category")
            
            if cat in QI_ENERGY_CATEGORIES: counts["qi"] += count
            elif cat in INTERNAL_ENERGY_CATEGORIES: counts["internal"] += count
            elif cat in MANA_ENERGY_CATEGORIES: counts["mana"] += count
            
            if "immortal" in kw_id or "deity" in kw_id or cat == "cultivation_realm":
                if kw.get("last_seen_unit", 0) >= self._total_chapters * 0.9:
                    immortal = True
                    imm_evidence.append(kw_id)

        energy = max(counts, key=counts.get) if sum(counts.values()) > 0 else "unknown"
        style = "cultivation" if energy == "qi" else "level-based" if energy == "mana" else "unknown"
        return energy, immortal, style, imm_evidence

    def _detect_species(self, name):
        beast_score = 0
        for kw_id, count in self._char_kw_map.get(name, {}).items():
            if self._keywords[kw_id].get("category") in BEAST_CATEGORIES:
                beast_score += count
        
        species = "beast" if beast_score > 5 else "human"
        return species, (species == "human")

    def _detect_social(self, name, salience):
        partners = []
        for pair_key, data in self._pairs.items():
            if name not in [data.get("character_a"), data.get("character_b")]: continue
            if data.get("persistence_score", 0) > ROMANTIC_PERSISTENCE_THRESHOLD:
                events = str(data.get("shared_event_list", [])).lower()
                if any(x in events for x in ["love", "marriage", "kiss", "husband", "wife"]):
                    other = data["character_b"] if data["character_a"] == name else data["character_a"]
                    partners.append(other)

        cardinality = len(partners)
        harem = "none"
        if cardinality >= 3:
            harem = "protagonist_harem" if salience >= PROTAGONIST_SALIENCE_THRESHOLD else "reverse_harem"
        return cardinality, harem, partners

    def _get_temporal_keywords(self, name):
        early, late = [], []
        late_start = self._total_chapters * 0.9
        for kw_id in self._char_kw_map.get(name, {}).keys():
            kw = self._keywords[kw_id]
            if 0 <= kw.get("first_seen_unit", -1) <= self._early_story_threshold: early.append(kw_id)
            if kw.get("last_seen_unit", -1) >= late_start: late.append(kw_id)
        return early, late

    def generate_profile(self, name, salience) -> CharacterProfile:
        role = self._classify_role(salience)
        inf_g, orig_g, g_chg, g_ev = self._infer_gender(name)
        spec, human = self._detect_species(name)
        o_type, o_era, o_ev = self._detect_origin(name)
        p_en, p_imm, p_sty, p_ev = self._detect_power_system(name)
        r_card, r_harem, r_partners = self._detect_social(name, salience)
        early_kw, late_kw = self._get_temporal_keywords(name)
        
        return CharacterProfile(
            character_name=name,
            role=role,
            salience_score=salience,
            identity=CharacterIdentity(inf_g, orig_g, g_chg, spec, human),
            origin_state=CharacterOriginState(o_type, o_era, o_ev),
            power_system=CharacterPowerSystem(p_en, p_imm, p_sty, p_ev),
            social=CharacterSocial(r_card, r_harem, "unknown", r_partners),
            evidence_summary=CharacterEvidenceSummary(g_ev, o_ev, p_ev, early_kw, late_kw)
        )

# --------------------------------------------------
# Main Runners
# --------------------------------------------------

def build_character_profiles(novel_name: str, run_id: str) -> CharacterProfilesMap:
    salience_data = _load_character_salience(novel_name, run_id)
    relationship_data = _load_relationship_matrix(novel_name, run_id)
    keyword_data = _load_event_keywords(novel_name, run_id)
    
    profiler = CharacterStateProfiler(salience_data, relationship_data, keyword_data)
    total_chapters = keyword_data.get("total_chapters", 0) if keyword_data else 0
    
    profiles = {}
    p_count, s_count = 0, 0
    for char_data in (salience_data.get("characters", []) if salience_data else []):
        name, score = char_data.get("name", ""), char_data.get("salience_score", 0.0)
        if score < 0.1: continue
        
        profile = profiler.generate_profile(name, score)
        profiles[name] = profile
        if profile.role == "protagonist": p_count += 1
        elif profile.role == "supporting": s_count += 1
    
    return CharacterProfilesMap(
        novel_name=novel_name, run_id=run_id, total_chapters=total_chapters,
        total_characters_profiled=len(profiles), protagonist_count=p_count,
        supporting_count=s_count, profiles=profiles
    )

def save_character_profiles(profiles_map: CharacterProfilesMap) -> str:
    novel_dir = os.path.join(CHARACTER_PROFILES_DIR, profiles_map.novel_name)
    os.makedirs(novel_dir, exist_ok=True)
    path = os.path.join(novel_dir, f"{profiles_map.run_id}.character_profiles.json")
    
    def _dt(obj):
        if hasattr(obj, "__dataclass_fields__"): return {k: _dt(v) for k, v in asdict(obj).items()}
        if isinstance(obj, dict): return {k: _dt(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_dt(v) for v in obj]
        return obj

    with open(path, "w", encoding="utf-8") as f: json.dump(_dt(profiles_map), f, indent=2, ensure_ascii=False)
    return path

def generate_character_profiles(novel_name: str, run_id: str) -> None:
    profiles_map = build_character_profiles(novel_name, run_id)
    save_character_profiles(profiles_map)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("novel_name")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    generate_character_profiles(args.novel_name, args.run_id or f"standalone_{args.novel_name}")