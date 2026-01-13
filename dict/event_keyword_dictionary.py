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
# v1.0.1 (2026-01-13): Completely revamped terms for better specificity
KEYWORD_DICTIONARY_VERSION = "1.0.1"

KEYWORD_DICTIONARY = {
    # --------------------------------------------------
    # Cultivation Realms
    # --------------------------------------------------
    "mortal_realm": {
        "terms": ["mortal realm", "mortal body", "mortal stage"],
        "category": "cultivation_realm",
    },
    "qi_condensation": {
        "terms": ["qi condensation", "condensing qi", "qi gathering"],
        "category": "cultivation_realm",
    },
    "foundation_establishment": {
        "terms": ["foundation establishment", "foundation building"],
        "category": "cultivation_realm",
    },
    "core_formation": {
        "terms": ["core formation", "golden core"],
        "category": "cultivation_realm",
    },
    "nascent_soul": {
        "terms": ["nascent soul", "nascent soul realm"],
        "category": "cultivation_realm",
    },
    "soul_transformation": {
        "terms": ["soul transformation", "spirit transformation"],
        "category": "cultivation_realm",
    },
    "void_refinement": {
        "terms": ["void refinement", "void stage"],
        "category": "cultivation_realm",
    },
    "dao_seeking": {
        "terms": ["dao seeking", "seeking the dao"],
        "category": "cultivation_realm",
    },
    "immortal_ascension": {
        "terms": ["immortal ascension", "ascended to immortality"],
        "category": "cultivation_realm",
    },
    "true_immortal": {
        "terms": ["true immortal", "immortal realm"],
        "category": "cultivation_realm",
    },
    "body_refinement": {
        "terms": ["body tempering", "tempering stage", "fleshly body", "body refinement"],
        "category": "cultivation_realm",
    },
    "blood_rebirth": {
        "terms": ["blood rebirth", "undying body", "regeneration stage"],
        "category": "cultivation_realm",
    },
    "saint_physique": {
        "terms": ["saint physique", "godly body", "sovereign body"],
        "category": "cultivation_realm",
    },
    "tribulation_transcendence": {
        "terms": ["tribulation transcendence", "crossing tribulation", "lightning tribulation"],
        "category": "cultivation_realm",
    },
    "mahayana": {
        "terms": ["mahayana stage", "great perfection", "limit of the mortal"],
        "category": "cultivation_realm",
    },
    "half_step_immortal": {
        "terms": ["half-step immortal", "pseudo-immortal", "mortal shedder"],
        "category": "cultivation_realm",
    },
    "earth_immortal": {
        "terms": ["earth immortal", "land immortal"],
        "category": "cultivation_realm",
    },
    "heavenly_immortal": {
        "terms": ["heavenly immortal", "celestial immortal"],
        "category": "cultivation_realm",
    },
    "mystic_immortal": {
        "terms": ["mystic immortal", "profound immortal"],
        "category": "cultivation_realm",
    },
    "golden_immortal": {
        "terms": ["golden immortal", "da luo golden immortal", "immortal lord"],
        "category": "cultivation_realm",
    },
    "immortal_king": {
        "terms": ["immortal king", "immortal monarch", "immortal venerable"],
        "category": "cultivation_realm",
    },
    "immortal_emperor": {
        "terms": ["immortal emperor", "sovereign", "supreme immortal"],
        "category": "cultivation_realm",
    },
    "demigod": {
        "terms": ["demigod", "false god", "quasi-god"],
        "category": "cultivation_realm",
    },
    "god_realm": {
        "terms": ["godhood", "divine realm", "true god", "god king"],
        "category": "cultivation_realm",
    },
    "world_creator": {
        "terms": ["world creator", "creation realm", "world tree stage"],
        "category": "cultivation_realm",
    },
    "law_comprehension": {
        "terms": ["law stage", "rule comprehension", "origin of laws"],
        "category": "cultivation_realm",
    },
    "dao_ancestor": {
        "terms": ["dao ancestor", "progenitor", "source realm"],
        "category": "cultivation_realm",
    },
    "transcendence": {
        "terms": ["transcendence", "eternal realm", "beyond the dao", "unfettered"],
        "category": "cultivation_realm",
    },

    # --------------------------------------------------
    # Sects, inheritance & cultivation society
    # --------------------------------------------------
    "sect": {
        "terms": ["cultivation sect", "inner sect", "outer sect"],
        "category": "cultivation_society",
    },
    "elder": {
        "terms": ["sect elder", "great elder"],
        "category": "cultivation_society",
    },
    "sect_master": {
        "terms": ["sect master", "sect leader"],
        "category": "cultivation_society",
    },
    "inheritance": {
        "terms": ["ancient inheritance", "inheritance ground", "immortal inheritance"],
        "category": "cultivation_society",
    },
    "sect_disciples": {
        "terms": ["outer disciple", "inner disciple", "core disciple", "legacy disciple", "true disciple",
                  "closed-door disciple"],
        "category": "cultivation_society",
    },
    "sect_leadership": {
        "terms": ["sect master", "sect leader", "patriarch", "palace master", "valley master"],
        "category": "cultivation_society",
    },
    "hidden_powerhouses": {
        "terms": ["grand elder", "supreme elder", "founding ancestor", "venerable", "supreme being"],
        "category": "cultivation_society",
    },
    "alchemy_guild": {
        "terms": ["alchemist guild", "pill pavilion", "medicine hall", "alchemist", "grandmaster alchemist"],
        "category": "cultivation_society",
    },
    "merchant_unions": {
        "terms": ["treasure pavilion"],
        "category": "cultivation_society",
    },
    "specialized_professions": {
        "terms": ["array master", "talisman master", "artifact refiner"],
        "category": "cultivation_society",
    },
    "cultivation_clan": {
        "terms": ["ancient clan"],
        "category": "cultivation_society",
    },
    "inheritance_sites": {
        "terms": ["ancient ruin", "secret realm", "inheritance ground", "immortal cave"],
        "category": "cultivation_society",
    },
    "legacy_items": {
        "terms": ["jade slip", "merit manual", "cultivation technique", "divine art"],
        "category": "cultivation_society",
    },
    "sect_events": {
        "terms": ["sect competition", "grand assembly", "disciple recruitment", "inner sect trial", "heavenly ranking"],
        "category": "cultivation_society",
    },
    "factions": {
        "terms": ["righteous path", "demonic path", "heretic sect", "neutral faction", "rogue cultivator"],
        "category": "cultivation_society",
    },
# --------------------------------------------------
    # Gender & Social Indicators (Tags: Male/Female Protag, Loli, Yaoi/Yuri)
    # --------------------------------------------------
    "male_honorifics": {
        "terms": ["young master", "senior brother", "junior brother", "sect brother", "patriarch", "fellow daoist", "mister"],
        "category": "gender_indicator_male",
    },
    "female_honorifics": {
        "terms": ["fairy", "jade beauty", "senior sister", "junior sister", "sect sister", "matriarch", "lady", "madam"],
        "category": "gender_indicator_female",
    },
    "loli_signals": {
        "terms": ["little girl", "petite", "child-like", "younger sister", "small stature"],
        "category": "age_indicator_young",
    },

    # --------------------------------------------------
    # Origin & Meta (Tags: Transmigration, Reincarnation, Regression)
    # --------------------------------------------------
    "modern_world_signals": {
        "terms": ["earth", "modern", "internet", "smartphone", "computer", "truck", "office worker", "high school student", "21st century", "science", "technology"],
        "category": "origin_modern",
    },
    "transmigration_events": {
        "terms": ["transmigrated", "isekai", "original owner", "possessing the body", "this body", "another world", "summoned"],
        "category": "origin_event",
    },
    "reincarnation_events": {
        "terms": ["reincarnated", "reborn", "previous life", "past life", "baby", "infant", "crying", "born again"],
        "category": "origin_event",
    },
    "regression_events": {
        "terms": ["regressed", "returned to the past", "second chance", "start over", "reversing time", "back in time"],
        "category": "origin_event",
    },

    # --------------------------------------------------
    # Power Systems (Genres: Wuxia vs Xianxia vs Xuanhuan)
    # --------------------------------------------------
    "wuxia_specific": {
        "terms": ["jianghu", "martial forest", "lightfoot", "internal force", "meridians", "pressure points", "qinggong"],
        "category": "power_system_wuxia",
    },
    "xuanhuan_western_magic": {
        "terms": ["mana", "magic circle", "spell", "wizard", "mage", "knight", "dragon", "griffon", "staff", "chanting"],
        "category": "power_system_western",
    },
    "game_system_signals": {
        "terms": ["status window", "level up", "experience points", "skill points", "quest", "inventory", "attributes", "strength stat"],
        "category": "power_system_game",
    },

    # --------------------------------------------------
    # Species & Transformation (Tags: Race Change, Shapeshifter, Mythical Beast)
    # --------------------------------------------------
    "beast_transformation": {
        "terms": ["transformed", "shifted", "beast form", "scales", "claws", "wings", "bloodline awakening", "fur", "tail"],
        "category": "morphology_change",
    },
    "multiple_bodies": {
        "terms": ["clone", "avatar", "external body", "doppelganger", "split soul", "projection"],
        "category": "body_state",
    },

    # --------------------------------------------------
    # Social & Romance (Genres: Harem, Yaoi, Yuri | Tags: Marriage, Pregnancy)
    # --------------------------------------------------
    "romance_events": {
        "terms": ["confession", "first kiss", "affection", "blushing", "beloved", "engagement", "proposal"],
        "category": "social_romance",
    },
    "marriage_events": {
        "terms": ["wedding", "marriage", "bride", "groom", "vows", "concubine", "consort", "wife", "husband"],
        "category": "social_marriage",
    },
    "family_events": {
        "terms": ["pregnant", "pregnancy", "childbirth", "baby", "son", "daughter", "heir"],
        "category": "social_family",
    },
    "harem_rivalry": {
        "terms": ["jealousy", "inner palace", "rivalry", "favor", "monopolize"],
        "category": "social_harem",
    },

    # --------------------------------------------------
    # Adult Content & Action
    # --------------------------------------------------
    "adult_content": {
        "terms": ["dual cultivation", "bedroom", "naked", "intimacy", "moan", "passion", "heat", "arousal"],
        "category": "adult_signal",
    },
    "action_violence": {
        "terms": ["blood", "slaughter", "chaos", "explosion", "battle", "war", "killing", "deadly", "mutilation"],
        "category": "action_signal",
    },

    # --------------------------------------------------
    # World Settings (Tags: Ancient China, Fantasy World, Interdimensional)
    # --------------------------------------------------
    "ancient_china_setting": {
        "terms": ["forbidden city", "imperial palace", "dynasty", "official", "eunuch", "emperor", "courtyard", "tea house"],
        "category": "setting_ancient_china",
    },
    "interdimensional": {
        "terms": ["parallel world", "alternate dimension", "rift", "portal", "void", "multiverse"],
        "category": "setting_travel",
    }
}
