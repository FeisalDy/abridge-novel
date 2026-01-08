# Taxonomy version: tracks tag list source
# From: Feydar/novelupdates_tags (NovelUpdates tag taxonomy, curated)
TAG_TAXONOMY_VERSION = "1.0.0"

# Rule version: tracks rule logic changes
# Increment when rule definitions change
# v1.1.0: Actor-centric validation for marriage, betrayal
#         Added harem mutual exclusion penalty
#         New condition types: actor_event_match, harem_penalty
TAG_RULE_VERSION = "1.1.0"

# --------------------------------------------------
# Tag Taxonomy (Static, Versioned)
# --------------------------------------------------
#
# This taxonomy is drawn from NovelUpdates tag classifications (curated).
# Each tag has:
#   - name: Canonical identifier (lowercase, underscored)
#   - display_name: Human-readable name
#   - description: Documentation only (NEVER used as classifier)
#
# Only tags with implementable rules are included.
# Tags requiring subjective interpretation are EXCLUDED.

TAG_TAXONOMY = {
    # --------------------------------------------------
    # Transmigration / Reincarnation Tags
    # --------------------------------------------------
    "reincarnation": {
        "display_name": "Reincarnation",
        "description": "Protagonist is born again after dying.",
    },
    "age_regression": {
        "display_name": "Age Regression",
        "description": "Protagonist grows younger instead of older, regaining youth.",
    },
    "body_swap": {
        "display_name": "Body Swap",
        "description": "Body swapping is an important part of the story.",
    },
    "sharing_a_body": {
        "display_name": "Sharing A Body",
        "description": "Two or more people sharing the same body.",
    },
    "race_change": {
        "display_name": "Race Change",
        "description": "Protagonist changes species during their current lifetime.",
    },

    # --------------------------------------------------
    # Cultivation Tags
    # --------------------------------------------------
    "cultivation": {
        "display_name": "Cultivation",
        "description": "Protagonist pursues immortality through Qi accumulation.",
    },

    # --------------------------------------------------
    # Power Level Tags
    # --------------------------------------------------
    "overpowered_protagonist": {
        "display_name": "Overpowered Protagonist",
        "description": "Protagonist is overpowered by story standards.",
    },

    # --------------------------------------------------
    # Relationship Tags
    # --------------------------------------------------
    "marriage": {
        "display_name": "Marriage",
        "description": "Protagonist gets married during the story.",
    },
    "arranged_marriage": {
        "display_name": "Arranged Marriage",
        "description": "Protagonist is part of an arranged marriage.",
    },
    "broken_engagement": {
        "display_name": "Broken Engagement",
        "description": "Story contains a broken engagement involving protagonist.",
    },
    "engagement": {
        "display_name": "Engagement",
        "description": "Protagonist engagement is a major plot point.",
    },
    "divorce": {
        "display_name": "Divorce",
        "description": "Protagonist involved in or significantly affected by divorce.",
    },
    "polygamy": {
        "display_name": "Polygamy",
        "description": "Male protagonist married to more than one female.",
    },
    "polyandry": {
        "display_name": "Polyandry",
        "description": "Female protagonist has more than one husband.",
    },
    "reverse_harem": {
        "display_name": "Reverse Harem",
        "description": "Female protagonist surrounded by multiple male interests.",
    },
    "incest": {
        "display_name": "Incest",
        "description": "Romantic interest between closely blood-related people.",
    },
    "adultery": {
        "display_name": "Adultery",
        "description": "Sexual relationship involving a married person.",
    },
    "affair": {
        "display_name": "Affair",
        "description": "Secret romantic/sexual relationship without partner knowing.",
    },
    "bickering_couple": {
        "display_name": "Bickering Couple",
        "description": "Main couple is always bickering.",
    },

    # --------------------------------------------------
    # Protagonist Gender Tags
    # --------------------------------------------------
    "female_protagonist": {
        "display_name": "Female Protagonist",
        "description": "Protagonist is biologically female.",
    },
    "male_to_female": {
        "display_name": "Male to Female",
        "description": "Male protagonist transformed to female.",
    },
    "female_to_male": {
        "display_name": "Female to Male",
        "description": "Female character transformed to male.",
    },
    "genderless_protagonist": {
        "display_name": "Genderless Protagonist",
        "description": "Protagonist has no particular gender.",
    },
    "bisexual_protagonist": {
        "display_name": "Bisexual Protagonist",
        "description": "Protagonist has romantic affiliations with multiple genders.",
    },

    # --------------------------------------------------
    # Protagonist Form Tags
    # --------------------------------------------------
    "humanoid_protagonist": {
        "display_name": "Humanoid Protagonist",
        "description": "Protagonist is not human but has humanoid form.",
    },
    "non_humanoid_protagonist": {
        "display_name": "Non-humanoid Protagonist",
        "description": "Protagonist is not a conventional human.",
    },
    "clones": {
        "display_name": "Clones",
        "description": "Protagonist can make or has clones.",
    },
    "multiple_bodies": {
        "display_name": "Protagonist with Multiple Bodies",
        "description": "Protagonist has multiple bodies or clones.",
    },
    "transformation_ability": {
        "display_name": "Transformation Ability",
        "description": "Protagonist can transform body shape freely.",
    },
    "appearance_changes": {
        "display_name": "Appearance Changes",
        "description": "Protagonist experiences drastic appearance changes.",
    },

    # --------------------------------------------------
    # Age Tags
    # --------------------------------------------------
    "child_protagonist": {
        "display_name": "Child Protagonist",
        "description": "Protagonist is a child for significant part of story.",
    },
    "elderly_protagonist": {
        "display_name": "Elderly Protagonist",
        "description": "Protagonist is old enough to have grandchildren.",
    },
    "age_progression": {
        "display_name": "Age Progression",
        "description": "Protagonist visibly ages throughout story.",
    },

    # --------------------------------------------------
    # Betrayal / Conflict Tags
    # --------------------------------------------------
    "betrayal": {
        "display_name": "Betrayal",
        "description": "Protagonist is betrayed or betrays someone.",
    },

    # --------------------------------------------------
    # Story Structure Tags
    # --------------------------------------------------
    "multiple_protagonists": {
        "display_name": "Multiple Protagonists",
        "description": "Story has more than one protagonist.",
    },
    "prophecies": {
        "display_name": "Prophecies",
        "description": "Prophecy influences protagonist or story.",
    },
    "fanfiction": {
        "display_name": "Fanfiction",
        "description": "Story based on a published work.",
    },

    # --------------------------------------------------
    # Setting Tags
    # --------------------------------------------------
    "ancient_china": {
        "display_name": "Ancient China",
        "description": "Story set in authentic Ancient Chinese environment.",
    },
    "ancient_times": {
        "display_name": "Ancient Times",
        "description": "Story set in ancient times (not China).",
    },
    "nobles": {
        "display_name": "Nobles",
        "description": "Protagonist or characters have noble titles.",
    },
    "imperial_harem": {
        "display_name": "Imperial Harem",
        "description": "Harem storyline involving royalty's palace.",
    },

    # --------------------------------------------------
    # Pregnancy / Family Tags
    # --------------------------------------------------
    "pregnancy": {
        "display_name": "Pregnancy",
        "description": "Protagonist or partner becomes pregnant.",
    },

    # --------------------------------------------------
    # Character Behavior Tags (Detectable)
    # --------------------------------------------------
    "manipulative_characters": {
        "display_name": "Manipulative Characters",
        "description": "Protagonist or significant characters psychologically manipulate others.",
    },
    "sadistic_characters": {
        "display_name": "Sadistic Characters",
        "description": "Character derives pleasure from inflicting pain/suffering.",
    },
}

# --------------------------------------------------
# Tag Rules (Static, Versioned, Explicit)
# --------------------------------------------------
#
# Each rule defines:
#   - base_score: Awarded when ALL required evidence is met
#   - required: Dict of evidence that MUST be present (hard gate)
#   - boosts: List of (condition_type, condition_value, score) tuples
#   - penalties: List of (condition_type, condition_value, score) tuples
#
# Condition types (inherited from genre_resolver + new):
#   - "keyword_present": Check if keyword_id exists in event keywords
#   - "category_present": Check if category exists in event keywords
#   - "keyword_spread": Check if keyword has narrative_spread >= value
#   - "keyword_density": Check if keyword has density >= value
#   - "category_count": Check if category has >= N keywords present
#   - "salient_pair_persistence": Check if any pair has persistence >= value
#   - "salient_character_count": Check if >= N characters have salience >= value
#   - "high_persistence_pair_count": Check if >= N pairs have persistence >= value
#   - "genre_present": Check if genre is resolved with confidence >= threshold
#   - "genre_confidence": Check if genre confidence >= specific value
#   - "actor_event_match": (keyword_id, min_salience, min_persistence)
#                          Check if keyword is linked to actor meeting salience OR persistence threshold
#                          REQUIRES: Tier-2 event_links and Tier-3.3 associated_characters
#   - "harem_penalty": threshold (float)
#                      Returns True if harem genre confidence >= threshold (triggers penalty)
#                      Used for mutual exclusion logic (e.g., harem vs marriage)
#
# DOCUMENTATION: Each rule includes inline comments explaining WHY
# these specific evidence items were chosen.

TAG_RULES = {
    # --------------------------------------------------
    # REINCARNATION
    # --------------------------------------------------
    # Reincarnation requires explicit reincarnation keyword presence.
    # Genre alignment boosts confidence.
    "reincarnation": {
        "base_score": 0.5,
        "required": {
            "keyword_present": ["reincarnation"],
        },
        "boosts": [
            # High spread indicates persistent reincarnation theme
            ("keyword_spread", ("reincarnation", 3), 0.15),
            # Genre alignment from isekai/reincarnation genre
            ("genre_present", "isekai", 0.10),
            ("genre_present", "reincarnation", 0.15),
            # Transmigration category indicates rebirth themes
            ("category_present", "transmigration", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # CULTIVATION
    # --------------------------------------------------
    # Cultivation tag requires cultivation category from keywords.
    # Xianxia/xuanhuan genre alignment boosts.
    "cultivation": {
        "base_score": 0.5,
        "required": {
            "category_present": ["cultivation"],
        },
        "boosts": [
            # Multiple cultivation keywords strengthen signal
            ("category_count", ("cultivation", 2), 0.15),
            # Xianxia genre alignment
            ("genre_present", "xianxia", 0.15),
            # Xuanhuan genre alignment
            ("genre_present", "xuanhuan", 0.10),
            # Breakthrough keyword persistence
            ("keyword_spread", ("breakthrough", 3), 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # BETRAYAL
    # --------------------------------------------------
    # Betrayal keyword MUST be linked to a salient actor to prevent
    # background noise triggers (e.g., side character mentions).
    # Actor validation ensures the betrayal involves main characters.
    "betrayal": {
        "base_score": 0.5,
        "required": {
            # Betrayal keyword must be linked to character with salience >= 0.4
            # OR character with relationship persistence >= 0.5
            "actor_event_match": ("betrayal", 0.4, 0.5),
        },
        "boosts": [
            # Spread indicates recurring betrayal theme
            ("keyword_spread", ("betrayal", 2), 0.15),
            # High density indicates betrayal-focused narrative
            ("keyword_density", ("betrayal", 0.5), 0.15),
            # Drama genre alignment
            ("genre_present", "drama", 0.10),
            # Tragedy genre alignment
            ("genre_present", "tragedy", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # MARRIAGE
    # --------------------------------------------------
    # Marriage requires actor-validated link to wedding/marriage keyword.
    # Must be linked to a salient character to ensure protagonist involvement.
    # MUTUAL EXCLUSION: High harem confidence applies heavy penalty,
    # reflecting narrative shift from monogamy to polygamy.
    "marriage": {
        "base_score": 0.4,
        "required": {
            # High persistence pair suggests committed relationship
            "salient_pair_persistence": 0.6,
        },
        "boosts": [
            # Romance genre alignment
            ("genre_present", "romance", 0.25),
            # Very high persistence indicates marriage-level commitment
            ("salient_pair_persistence", 0.8, 0.20),
            # Single focused relationship (not harem)
            ("high_persistence_pair_count", (1, 0.7), 0.15),
        ],
        "penalties": [
            # Multiple high persistence pairs suggest harem, not marriage
            ("high_persistence_pair_count", (3, 0.5), 0.20),
            # HAREM MUTUAL EXCLUSION: If harem confidence > 0.7, apply -0.5 penalty
            # This reflects narrative shift from monogamy to polygamy
            ("harem_penalty", 0.7, 0.50),
        ],
    },

    # --------------------------------------------------
    # POLYGAMY
    # --------------------------------------------------
    # Multiple high-persistence pairs + harem genre.
    "polygamy": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Multiple persistent relationships
            ("high_persistence_pair_count", (3, 0.5), 0.25),
            # Harem genre is direct signal
            ("genre_present", "harem", 0.25),
            # Many salient characters suggests multiple interests
            ("salient_character_count", (5, 0.2), 0.15),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # REVERSE HAREM
    # --------------------------------------------------
    # Female protagonist indicator + multiple male relationships.
    # Harder to detect without explicit gender info.
    "reverse_harem": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Multiple persistent pairs needed
            ("high_persistence_pair_count", (3, 0.5), 0.25),
            # Many salient characters
            ("salient_character_count", (5, 0.2), 0.15),
            # Romance genre
            ("genre_present", "romance", 0.15),
        ],
        "penalties": [
            # Harem genre typically implies male protagonist
            ("genre_present", "harem", 0.10),
        ],
    },

    # --------------------------------------------------
    # MULTIPLE PROTAGONISTS
    # --------------------------------------------------
    # Detectable through multiple high-salience characters.
    "multiple_protagonists": {
        "base_score": 0.3,
        "required": {
            # Need multiple high-salience characters
            "salient_character_count": (2, 0.7),
        },
        "boosts": [
            # More high-salience characters strengthen signal
            ("salient_character_count", (3, 0.6), 0.20),
            ("salient_character_count", (4, 0.5), 0.15),
            # Drama genre often has ensemble casts
            ("genre_present", "drama", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # AGE REGRESSION
    # --------------------------------------------------
    # Regression keyword + transmigration signals.
    "age_regression": {
        "base_score": 0.4,
        "required": {
            "keyword_present": ["regression"],
        },
        "boosts": [
            # Transmigration category alignment
            ("category_present", "transmigration", 0.15),
            # Second chance themes
            ("keyword_present", "second_chance", 0.15),
            # Reincarnation alignment
            ("genre_present", "reincarnation", 0.15),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # BODY SWAP / SHARING A BODY
    # --------------------------------------------------
    # Possession keyword is the signal.
    "body_swap": {
        "base_score": 0.4,
        "required": {
            "keyword_present": ["possession"],
        },
        "boosts": [
            # Transmigration category
            ("category_present", "transmigration", 0.15),
            # Transformation category
            ("category_present", "transformation", 0.15),
        ],
        "penalties": [],
    },

    "sharing_a_body": {
        "base_score": 0.4,
        "required": {
            "keyword_present": ["possession"],
        },
        "boosts": [
            # Transformation presence suggests shared body mechanics
            ("category_present", "transformation", 0.15),
            # Transmigration signals
            ("category_present", "transmigration", 0.15),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # TRANSFORMATION ABILITY / RACE CHANGE
    # --------------------------------------------------
    "transformation_ability": {
        "base_score": 0.4,
        "required": {
            "category_present": ["transformation"],
        },
        "boosts": [
            # Multiple transformation keywords
            ("category_count", ("transformation", 2), 0.15),
            # Awakening indicates power development
            ("keyword_present", "awakening", 0.15),
            # Supernatural genre alignment
            ("genre_present", "supernatural", 0.10),
        ],
        "penalties": [],
    },

    "race_change": {
        "base_score": 0.4,
        "required": {
            "category_present": ["transformation"],
        },
        "boosts": [
            # Transformation spread indicates ongoing changes
            ("category_count", ("transformation", 2), 0.15),
            # Fantasy genre alignment
            ("genre_present", "fantasy", 0.15),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # APPEARANCE CHANGES
    # --------------------------------------------------
    "appearance_changes": {
        "base_score": 0.4,
        "required": {
            "category_present": ["transformation"],
        },
        "boosts": [
            # Transformation keywords
            ("category_count", ("transformation", 2), 0.15),
            # Cultivation often involves physical transformation
            ("genre_present", "xianxia", 0.10),
            ("genre_present", "xuanhuan", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # CLONES / MULTIPLE BODIES
    # --------------------------------------------------
    "clones": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Transformation category
            ("category_present", "transformation", 0.20),
            # System genre (clone mechanics)
            ("genre_present", "system", 0.15),
            # Cultivation (clone cultivation techniques)
            ("genre_present", "xianxia", 0.15),
        ],
        "penalties": [],
    },

    "multiple_bodies": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            ("category_present", "transformation", 0.20),
            ("genre_present", "system", 0.15),
            ("genre_present", "xianxia", 0.15),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # ANCIENT CHINA / ANCIENT TIMES
    # --------------------------------------------------
    # Xianxia/wuxia genre strongly correlates with ancient China.
    "ancient_china": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Xianxia is almost always ancient China
            ("genre_present", "xianxia", 0.30),
            # Wuxia is ancient China martial arts
            ("genre_present", "wuxia", 0.30),
            # Xuanhuan often ancient China
            ("genre_present", "xuanhuan", 0.20),
            # Cultivation signal
            ("category_present", "cultivation", 0.15),
        ],
        "penalties": [
            # System/LitRPG suggests non-traditional setting
            ("genre_present", "system", 0.15),
            ("genre_present", "litrpg", 0.15),
        ],
    },

    "ancient_times": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Historical genre
            ("genre_present", "historical", 0.25),
            # Wuxia (if not China-specific)
            ("genre_present", "wuxia", 0.15),
            # Fantasy genre (often pseudo-medieval)
            ("genre_present", "fantasy", 0.15),
        ],
        "penalties": [
            # Xianxia is specifically China
            ("genre_present", "xianxia", 0.20),
            # System/LitRPG is modern concept
            ("genre_present", "system", 0.15),
        ],
    },

    # --------------------------------------------------
    # NOBLES / IMPERIAL HAREM
    # --------------------------------------------------
    "nobles": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Historical setting often involves nobles
            ("genre_present", "historical", 0.20),
            # Wuxia often has noble families
            ("genre_present", "wuxia", 0.15),
            # Drama with political themes
            ("genre_present", "drama", 0.15),
            # Multiple salient characters (large cast = noble intrigue)
            ("salient_character_count", (6, 0.2), 0.15),
        ],
        "penalties": [],
    },

    "imperial_harem": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Harem genre required
            ("genre_present", "harem", 0.25),
            # Historical setting
            ("genre_present", "historical", 0.15),
            # Multiple persistent pairs
            ("high_persistence_pair_count", (4, 0.4), 0.20),
            # Many salient characters
            ("salient_character_count", (7, 0.2), 0.15),
        ],
        "penalties": [
            # Modern genres contradict imperial setting
            ("genre_present", "system", 0.15),
            ("genre_present", "litrpg", 0.15),
        ],
    },

    # --------------------------------------------------
    # PROPHECIES
    # --------------------------------------------------
    # Discovery keywords + destiny themes.
    "prophecies": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Discovery category (secrets, revelations)
            ("category_present", "discovery", 0.20),
            # Secret keyword spread
            ("keyword_spread", ("secret", 2), 0.15),
            # Fantasy genre alignment
            ("genre_present", "fantasy", 0.15),
            # Xianxia often has fate/destiny
            ("genre_present", "xianxia", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # MANIPULATIVE CHARACTERS / SADISTIC CHARACTERS
    # --------------------------------------------------
    "manipulative_characters": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Betrayal indicates manipulation
            ("keyword_present", "betrayal", 0.25),
            # Secret keyword (hidden agendas)
            ("keyword_present", "secret", 0.15),
            # Drama genre
            ("genre_present", "drama", 0.15),
            # Mystery (plots and schemes)
            ("genre_present", "mystery", 0.15),
        ],
        "penalties": [],
    },

    "sadistic_characters": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Death keyword presence
            ("keyword_present", "death", 0.20),
            # Horror genre alignment
            ("genre_present", "horror", 0.20),
            # Tragedy genre
            ("genre_present", "tragedy", 0.15),
            # Betrayal themes
            ("keyword_present", "betrayal", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # PREGNANCY
    # --------------------------------------------------
    # Hard to detect without explicit keywords.
    # Romance + high persistence suggests family themes.
    "pregnancy": {
        "base_score": 0.2,
        "required": {},
        "boosts": [
            # Strong romance signal
            ("genre_present", "romance", 0.20),
            # Very high persistence pair (long-term relationship)
            ("salient_pair_persistence", 0.8, 0.20),
            # Slice of life (domestic themes)
            ("genre_present", "slice_of_life", 0.15),
        ],
        "penalties": [
            # Action-heavy unlikely to focus on pregnancy
            ("genre_present", "action", 0.10),
        ],
    },
}