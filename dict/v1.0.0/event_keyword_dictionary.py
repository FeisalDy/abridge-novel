"""
Event Keyword Dictionary
Static, versioned, lexical-only.
"""

# Guidelines:
# - Use specific terms to avoid false positives
# - Include common variations and aliases
# - Multi-word phrases are supported
# - All matching is case-insensitive

# VERSION HISTORY:
# v1.0.0 (2024-12-31): Initial dictionary with core isekai/cultivation terms
KEYWORD_DICTIONARY_VERSION = "1.0.0"

KEYWORD_DICTIONARY = {
    # --------------------------------------------------
    # Transmigration / Isekai Events
    # --------------------------------------------------
    "reincarnation": {
        "terms": ["reincarnation", "reincarnate", "reincarnated", "rebirth", "reborn"],
        "category": "transmigration",
    },
    "transmigration": {
        "terms": ["transmigration", "transmigrate", "transmigrated", "soul transfer"],
        "category": "transmigration",
    },
    "regression": {
        "terms": ["regression", "regress", "regressed", "time regression", "return to the past"],
        "category": "transmigration",
    },
    "second_chance": {
        "terms": ["second chance", "another chance", "new life", "fresh start"],
        "category": "transmigration",
    },

    # --------------------------------------------------
    # System / Game Elements
    # --------------------------------------------------
    "system_awakening": {
        "terms": ["system", "status window", "status screen", "game system", "awakening system"],
        "category": "system",
    },
    "level_up": {
        "terms": ["level up", "leveled up", "leveling", "level increase", "gained a level"],
        "category": "system",
    },
    "skill_acquisition": {
        "terms": ["skill acquired", "new skill", "skill unlocked", "learned skill", "skill gained"],
        "category": "system",
    },
    "quest": {
        "terms": ["quest", "mission", "task assigned", "objective"],
        "category": "system",
    },

    # --------------------------------------------------
    # Cultivation / Power Events
    # --------------------------------------------------
    "cultivation": {
        "terms": ["cultivation", "cultivate", "cultivating", "cultivator"],
        "category": "cultivation",
    },
    "breakthrough": {
        "terms": ["breakthrough", "break through", "broke through", "advancement", "realm advancement"],
        "category": "cultivation",
    },
    "enlightenment": {
        "terms": ["enlightenment", "enlightened", "comprehension", "insight", "epiphany"],
        "category": "cultivation",
    },
    "tribulation": {
        "terms": ["tribulation", "heavenly tribulation", "lightning tribulation", "thunder tribulation"],
        "category": "cultivation",
    },

    # --------------------------------------------------
    # Conflict / Combat Events
    # --------------------------------------------------
    "battle": {
        "terms": ["battle", "combat", "fight", "fighting", "fought", "clash"],
        "category": "conflict",
    },
    "death": {
        "terms": ["death", "died", "killed", "slain", "perished", "fallen"],
        "category": "conflict",
    },
    "revenge": {
        "terms": ["revenge", "vengeance", "avenge", "avenged", "retribution"],
        "category": "conflict",
    },
    "betrayal": {
        "terms": ["betrayal", "betrayed", "betrayer", "treachery", "backstab"],
        "category": "conflict",
    },

    # --------------------------------------------------
    # Discovery / Acquisition Events
    # --------------------------------------------------
    "treasure": {
        "terms": ["treasure", "artifact", "relic", "inheritance", "legacy"],
        "category": "discovery",
    },
    "secret": {
        "terms": ["secret", "hidden", "concealed", "mystery", "mysterious"],
        "category": "discovery",
    },
    "awakening": {
        "terms": ["awakening", "awakened", "awaken", "dormant power"],
        "category": "discovery",
    },

    # --------------------------------------------------
    # World Events
    # --------------------------------------------------
    "apocalypse": {
        "terms": ["apocalypse", "apocalyptic", "end of the world", "cataclysm", "catastrophe"],
        "category": "world_event",
    },
    "war": {
        "terms": ["war", "warfare", "invasion", "conquest", "siege"],
        "category": "world_event",
    },
    "tournament": {
        "terms": ["tournament", "competition", "contest", "championship", "arena"],
        "category": "world_event",
    },

    # --------------------------------------------------
    # Transformation Events
    # --------------------------------------------------
    "transformation": {
        "terms": ["transformation", "transformed", "transform", "metamorphosis", "evolution"],
        "category": "transformation",
    },
    "possession": {
        "terms": ["possession", "possessed", "possess", "body takeover", "soul possession"],
        "category": "transformation",
    },
    "resurrection": {
        "terms": ["resurrection", "resurrected", "brought back", "revived", "revival"],
        "category": "transformation",
    },
}
