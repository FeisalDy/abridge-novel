# --------------------------------------------------
# Genre Taxonomy (Static, Versioned)
# --------------------------------------------------
#
# This taxonomy is drawn from NovelUpdates genre classifications.
# Each genre has:
#   - name: Canonical identifier (lowercase, underscored)
#   - display_name: Human-readable name
#   - description: Documentation only (NEVER used as classifier)
#
# Only genres with implementable rules are included.
GENRE_TAXONOMY_VERSION = "1.0.0"
GENRE_TAXONOMY = {
    # --------------------------------------------------
    # Eastern Fantasy Genres
    # --------------------------------------------------
    "xianxia": {
        "display_name": "Xianxia",
        "description": "Martial arts stories about cultivating to immortality, influenced by Chinese mythology and Daoism.",
    },
    "xuanhuan": {
        "display_name": "Xuanhuan",
        "description": "Cultivation stories with broader fantasy elements, not strictly tied to Chinese mythology.",
    },
    "wuxia": {
        "display_name": "Wuxia",
        "description": "Martial arts stories about mortal humans achieving superhuman abilities, typically in ancient China settings. No immortality.",
    },
    "martial_arts": {
        "display_name": "Martial Arts",
        "description": "Stories focusing on combat arts and self-defense disciplines.",
    },

    # --------------------------------------------------
    # Isekai / Transmigration Genres
    # --------------------------------------------------
    "isekai": {
        "display_name": "Isekai",
        "description": "Stories involving transportation or reincarnation to another world.",
    },
    "reincarnation": {
        "display_name": "Reincarnation",
        "description": "Stories where the protagonist is reborn, often with memories of a past life.",
    },

    # --------------------------------------------------
    # System / GameLit Genres
    # --------------------------------------------------
    "system": {
        "display_name": "System",
        "description": "Stories featuring game-like systems, status windows, or progression mechanics.",
    },
    "litrpg": {
        "display_name": "LitRPG",
        "description": "Stories with explicit RPG mechanics like levels, skills, and stats.",
    },

    # --------------------------------------------------
    # Core Genres
    # --------------------------------------------------
    "action": {
        "display_name": "Action",
        "description": "Stories depicting fighting, violence, and fast-paced motion.",
    },
    "adventure": {
        "display_name": "Adventure",
        "description": "Stories about exploring new places and encountering challenges.",
    },
    "fantasy": {
        "display_name": "Fantasy",
        "description": "Stories involving magic, mythical creatures, or supernatural elements.",
    },
    "romance": {
        "display_name": "Romance",
        "description": "Stories focusing heavily on romantic relationships.",
    },
    "drama": {
        "display_name": "Drama",
        "description": "Stories meant to evoke emotional responses through conflict.",
    },
    "mystery": {
        "display_name": "Mystery",
        "description": "Stories centered on unexplained events and investigation.",
    },
    "horror": {
        "display_name": "Horror",
        "description": "Stories focused on fear and terror.",
    },
    "tragedy": {
        "display_name": "Tragedy",
        "description": "Stories featuring events of great loss and misfortune.",
    },

    # --------------------------------------------------
    # Demographic Genres (Not implemented - require external metadata)
    # --------------------------------------------------
    # shounen, shoujo, seinen, josei - require reader demographic data

    # --------------------------------------------------
    # Setting-Based Genres
    # --------------------------------------------------
    "historical": {
        "display_name": "Historical",
        "description": "Stories set in a historical period or following historical events.",
    },
    "school_life": {
        "display_name": "School Life",
        "description": "Stories with school as a major setting.",
    },
    "supernatural": {
        "display_name": "Supernatural",
        "description": "Stories involving powers or events that defy natural laws.",
    },

    # --------------------------------------------------
    # Special Genres
    # --------------------------------------------------
    "harem": {
        "display_name": "Harem",
        "description": "Stories with one character attracting multiple romantic interests.",
    },
    "gender_bender": {
        "display_name": "Gender Bender",
        "description": "Stories involving gender transformation or cross-dressing.",
    },
    "slice_of_life": {
        "display_name": "Slice of Life",
        "description": "Naturalistic stories focusing on everyday life without a focused plot.",
    },
}

# --------------------------------------------------
# Genre Rules (Static, Versioned, Explicit)
# --------------------------------------------------
#
# Each rule defines:
#   - base_score: Awarded when ALL required evidence is met
#   - required: Dict of evidence that MUST be present (hard gate)
#   - boosts: List of (condition_type, condition_value, score) tuples
#   - penalties: List of (condition_type, condition_value, score) tuples
#
# Condition types:
#   - "keyword_present": Check if keyword_id exists in event keywords
#   - "category_present": Check if category exists in event keywords
#   - "category_with_actor": Check if category has keyword linked to salient actor
#                            Value: (category_id, min_salience) tuple
#                            REQUIRES: Regenerated Tier-2 (event_links) and Tier-3.3 (associated_characters)
#   - "keyword_spread": Check if keyword has narrative_spread >= value
#   - "keyword_density": Check if keyword has density >= value
#   - "category_count": Check if category has >= N keywords present
#   - "salient_pair_persistence": Check if any pair has persistence >= value
#   - "salient_character_count": Check if >= N characters have salience >= value
#
# DOCUMENTATION: Each rule includes inline comments explaining WHY
# these specific evidence items were chosen.
GENRE_RULE_VERSION = "1.1.0"
GENRE_RULES = {
    # --------------------------------------------------
    # XIANXIA
    # --------------------------------------------------
    # Xianxia requires cultivation + immortality-seeking themes.
    # Strong signal: tribulation, enlightenment keywords
    # The presence of "cultivation" category linked to a SALIENT ACTOR is the hard gate.
    # This prevents false positives from side character mentions.
    "xianxia": {
        "base_score": 0.5,
        "required": {
            # Cultivation keywords linked to salient character (salience >= 0.5)
            # This ensures the protagonist/main character is involved in cultivation
            "category_with_actor": ("cultivation", 0.5),
        },
        "boosts": [
            # Tribulation is iconic xianxia element
            ("keyword_present", "tribulation", 0.15),
            # Enlightenment/comprehension is core cultivation trope
            ("keyword_present", "enlightenment", 0.10),
            # Breakthrough persistence indicates sustained cultivation arc
            ("keyword_spread", ("breakthrough", 3), 0.10),
            # Multiple cultivation keywords strengthen signal
            ("category_count", ("cultivation", 2), 0.10),
            # Transmigration common in xianxia
            ("category_present", "transmigration", 0.05),
        ],
        "penalties": [
            # System/LitRPG elements push toward xuanhuan, not pure xianxia
            ("category_present", "system", 0.10),
        ],
    },

    # --------------------------------------------------
    # XUANHUAN
    # --------------------------------------------------
    # Xuanhuan is cultivation + non-traditional elements (system, isekai)
    # Broader than xianxia, accepts western fantasy fusion
    # Uses category_with_actor to ensure main character involvement
    "xuanhuan": {
        "base_score": 0.4,
        "required": {
            # Cultivation linked to salient actor (slightly lower threshold)
            "category_with_actor": ("cultivation", 0.4),
        },
        "boosts": [
            # System elements push cultivation stories toward xuanhuan
            ("category_present", "system", 0.20),
            # Isekai/transmigration fusion is common xuanhuan pattern
            ("category_present", "transmigration", 0.15),
            # Multiple cultivation keywords
            ("category_count", ("cultivation", 2), 0.10),
            # Transformation themes common in xuanhuan
            ("category_present", "transformation", 0.05),
        ],
        "penalties": [
            # Pure tribulation without system suggests xianxia, not xuanhuan
            ("keyword_present", "tribulation", 0.05),
        ],
    },

    # --------------------------------------------------
    # WUXIA
    # --------------------------------------------------
    # Wuxia is martial arts WITHOUT immortality cultivation.
    # Human-scale superhuman abilities through training.
    "wuxia": {
        "base_score": 0.4,
        "required": {
            # Conflict category indicates combat focus
            "category_present": ["conflict"],
        },
        "boosts": [
            # Battle keyword persistence indicates sustained martial action
            ("keyword_spread", ("battle", 2), 0.15),
            # Revenge is classic wuxia motivation
            ("keyword_present", "revenge", 0.15),
            # Multiple characters with moderate salience (ensemble cast)
            ("salient_character_count", (3, 0.3), 0.10),
        ],
        "penalties": [
            # Cultivation pushes toward xianxia/xuanhuan, not wuxia
            ("category_present", "cultivation", 0.20),
            # System elements are not traditional wuxia
            ("category_present", "system", 0.15),
            # Immortality themes contradict wuxia's mortal focus
            ("keyword_present", "tribulation", 0.10),
        ],
    },

    # --------------------------------------------------
    # ISEKAI / REINCARNATION
    # --------------------------------------------------
    # Stories about transportation or rebirth to another world/life
    "isekai": {
        "base_score": 0.5,
        "required": {
            "category_present": ["transmigration"],
        },
        "boosts": [
            # Reincarnation keyword with spread indicates core theme
            ("keyword_spread", ("reincarnation", 2), 0.15),
            # Transmigration keyword directly indicates isekai
            ("keyword_present", "transmigration", 0.15),
            # Regression (time-loop isekai variant)
            ("keyword_present", "regression", 0.10),
            # System elements common in modern isekai
            ("category_present", "system", 0.10),
        ],
        "penalties": [],
    },

    "reincarnation": {
        "base_score": 0.5,
        "required": {
            # Explicit reincarnation keyword required
            "keyword_present": ["reincarnation"],
        },
        "boosts": [
            # Spread indicates sustained reincarnation theme
            ("keyword_spread", ("reincarnation", 3), 0.15),
            # High density indicates narrative focus on reincarnation
            ("keyword_density", ("reincarnation", 1.0), 0.15),
            # Second chance themes align with reincarnation
            ("keyword_present", "second_chance", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # SYSTEM / LITRPG
    # --------------------------------------------------
    # Stories with explicit game mechanics
    # Uses category_with_actor to ensure the system is linked to a main character,
    # not just mentioned by side characters.
    "system": {
        "base_score": 0.5,
        "required": {
            # System keywords linked to salient character (salience >= 0.5)
            "category_with_actor": ("system", 0.5),
        },
        "boosts": [
            # System awakening spread indicates sustained system presence
            ("keyword_spread", ("system_awakening", 2), 0.15),
            # Level-up keywords indicate progression focus
            ("keyword_present", "level_up", 0.15),
            # Skills indicate game-like mechanics
            ("keyword_present", "skill_acquisition", 0.10),
            # Quest indicates game structure
            ("keyword_present", "quest", 0.10),
        ],
        "penalties": [],
    },

    "litrpg": {
        "base_score": 0.4,
        "required": {
            "category_present": ["system"],
        },
        "boosts": [
            # Level-up is THE defining LitRPG element
            ("keyword_present", "level_up", 0.20),
            # Skill acquisition indicates RPG mechanics
            ("keyword_present", "skill_acquisition", 0.15),
            # Quest system indicates RPG structure
            ("keyword_present", "quest", 0.10),
            # Multiple system keywords indicate deep RPG integration
            ("category_count", ("system", 3), 0.10),
        ],
        "penalties": [
            # No level-up strongly penalizes LitRPG
            # (handled implicitly by missing boost)
        ],
    },

    # --------------------------------------------------
    # ACTION / ADVENTURE
    # --------------------------------------------------
    "action": {
        "base_score": 0.4,
        "required": {
            "category_present": ["conflict"],
        },
        "boosts": [
            # Battle keyword spread indicates sustained action
            ("keyword_spread", ("battle", 3), 0.20),
            # High battle density indicates action-heavy narrative
            ("keyword_density", ("battle", 0.5), 0.15),
            # Death/combat keywords reinforce action
            ("keyword_present", "death", 0.10),
            # Multiple conflict keywords
            ("category_count", ("conflict", 2), 0.10),
        ],
        "penalties": [],
    },

    "adventure": {
        "base_score": 0.3,
        "required": {
            # Adventure needs discovery or exploration signals
            "category_present": ["discovery"],
        },
        "boosts": [
            # Treasure/inheritance indicates exploration
            ("keyword_present", "treasure", 0.15),
            # Secret/mystery indicates discovery focus
            ("keyword_present", "secret", 0.15),
            # World events indicate scope of adventure
            ("category_present", "world_event", 0.10),
            # Multiple discovery keywords
            ("category_count", ("discovery", 2), 0.10),
            # Conflict adds action-adventure flavor
            ("category_present", "conflict", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # FANTASY
    # --------------------------------------------------
    # Broad category: magic, supernatural, mythical elements
    "fantasy": {
        "base_score": 0.3,
        "required": {
            # Any supernatural-adjacent category qualifies
            # Using cultivation as proxy for fantasy elements
        },
        "boosts": [
            # Cultivation indicates eastern fantasy
            ("category_present", "cultivation", 0.20),
            # Transformation indicates magical elements
            ("category_present", "transformation", 0.15),
            # System indicates fantasy game world
            ("category_present", "system", 0.10),
            # Discovery indicates fantastical elements
            ("category_present", "discovery", 0.10),
            # Transmigration indicates otherworldly fantasy
            ("category_present", "transmigration", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # DRAMA / TRAGEDY
    # --------------------------------------------------
    "drama": {
        "base_score": 0.3,
        "required": {},  # No hard gate - drama is supplementary
        "boosts": [
            # Betrayal indicates interpersonal conflict
            ("keyword_present", "betrayal", 0.20),
            # Death indicates emotional stakes
            ("keyword_present", "death", 0.15),
            # Revenge indicates dramatic motivation
            ("keyword_present", "revenge", 0.15),
            # Multiple salient characters suggest character-driven story
            ("salient_character_count", (4, 0.2), 0.10),
            # Persistent character pairs suggest relationship focus
            ("salient_pair_persistence", 0.5, 0.10),
        ],
        "penalties": [],
    },

    "tragedy": {
        "base_score": 0.3,
        "required": {
            "keyword_present": ["death"],
        },
        "boosts": [
            # Death spread indicates persistent tragic theme
            ("keyword_spread", ("death", 3), 0.20),
            # Betrayal common in tragedy
            ("keyword_present", "betrayal", 0.15),
            # Apocalypse/cataclysm indicates tragic scale
            ("keyword_present", "apocalypse", 0.15),
            # War indicates mass tragedy
            ("keyword_present", "war", 0.10),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # MYSTERY / HORROR
    # --------------------------------------------------
    "mystery": {
        "base_score": 0.4,
        "required": {
            "keyword_present": ["secret"],
        },
        "boosts": [
            # Secret spread indicates ongoing mystery
            ("keyword_spread", ("secret", 3), 0.20),
            # High secret density indicates mystery focus
            ("keyword_density", ("secret", 0.5), 0.15),
            # Discovery category aligns with investigation
            ("category_count", ("discovery", 2), 0.15),
        ],
        "penalties": [],
    },

    "horror": {
        "base_score": 0.4,
        "required": {
            "category_present": ["conflict"],
        },
        "boosts": [
            # Death is core to horror
            ("keyword_present", "death", 0.20),
            # Apocalypse indicates horror scale
            ("keyword_present", "apocalypse", 0.15),
            # Possession indicates supernatural horror
            ("keyword_present", "possession", 0.15),
        ],
        "penalties": [
            # Cultivation/system shifts away from horror tone
            ("category_present", "cultivation", 0.15),
            ("category_present", "system", 0.10),
        ],
    },

    # --------------------------------------------------
    # HAREM
    # --------------------------------------------------
    # Requires multiple persistent character relationships
    "harem": {
        "base_score": 0.3,
        "required": {},  # No hard gate - evidence-based only
        "boosts": [
            # Multiple salient characters required for harem
            ("salient_character_count", (5, 0.2), 0.25),
            # High persistence pairs indicate relationship focus
            ("salient_pair_persistence", 0.6, 0.20),
            # Multiple high-persistence pairs
            ("high_persistence_pair_count", (3, 0.5), 0.20),
        ],
        "penalties": [],
    },

    # --------------------------------------------------
    # SUPERNATURAL
    # --------------------------------------------------
    "supernatural": {
        "base_score": 0.3,
        "required": {},
        "boosts": [
            # Transformation indicates supernatural elements
            ("category_present", "transformation", 0.20),
            # Possession is explicitly supernatural
            ("keyword_present", "possession", 0.20),
            # Resurrection defies natural law
            ("keyword_present", "resurrection", 0.15),
            # Awakening indicates supernatural powers
            ("keyword_present", "awakening", 0.15),
        ],
        "penalties": [],
    },
}

