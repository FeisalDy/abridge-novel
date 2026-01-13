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
GENRE_TAXONOMY_VERSION = "1.0.1"
GENRE_TAXONOMY = {
    "action": {
        "display_name": "Action",
        "description": "A work typically depicting fighting, violence, chaos, and fast paced motion.",
    },
    "adult": {
        "display_name": "Adult",
        "description": "Contains mature content that is suitable only for adults. Titles in this category may include prolonged scenes of intense violence and/or graphic sexual content and nudity.",
    },
    "adventure": {
        "display_name": "Adventure",
        "description": "Exploring new places, environments or situations. This is often associated with people on long journeys to places far away encountering amazing things.",
    },
    "fantasy": {
        "display_name": "Fantasy",
        "description": "Anything that involves, but not limited to, magic, dream world, and fairy tales.",
    },
    "gender_bender": {
        "display_name": "Gender Bender",
        "description": "Girls dressing up as guys, guys dressing up as girls. Guys turning into girls, girls turning into guys.",
    },
    "harem": {
        "display_name": "Harem",
        "description": "A series involving one male character and many female characters (usually attracted to the male character). A Reverse Harem is when the genders are reversed.",
    },
    "martial_arts": {
        "display_name": "Martial Arts",
        "description": "The novel has a focus on any of several arts of combat or self-defense. These may include aikido, karate, judo, or tae kwon do, kendo, fencing, and so on and so forth.",
    },
    "romance": {
        "display_name": "Romance",
        "description": "A story in this genre focus heavily on the romantic relationship between two or more people.",
    },
    "wuxia": {
        "display_name": "Wuxia",
        "description": "Wuxia is a fictional stories about mortal humans who can achieve superhuman ability through martial arts training or internal energy cultivation. Wuxia is usually depicted in an ancient china setting. Despite any existence of supernatural elements, characters in a wuxia are rarely depicted reaching over 150 years of age. No immortality.",
    },
    "xianxia": {
        "display_name": "Xianxia",
        "description": "Xianxia is fictional martial art stories where the main goal of the population is cultivating to Immortality, seeking eternal life and the pinnacle of strength. Xianxia stories features supernatural elements, influenced heavily by Chinese folklore/mythology. Cultivation path in xianxia involves taoism/daoism elements.",
    },
    "xuanhuan": {
        "display_name": "Xuanhuan",
        "description": "Similar to xianxia, Xuanhuan may contain immortal cultivation. However, unlike xianxia, which is more focused on becoming immortal and tighter on chinese mythology, Xuanhuan is a broader, more loose genre. Basically, if it's a cultivation-based story, yet it contain elements of western fantasy, such as sci-fi, or magic that's not inherently eastern, then it is a xuanhuan.",
    },
    "yaoi": {
        "display_name": "Yaoi",
        "description": "This work usually involves intimate relationships between men. Mutually exclusive with shounen ai.",
    },
    "yuri": {
        "display_name": "Yuri",
        "description": "This work usually involves intimate relationships between women. Mutually exclusive with shoujo ai.",
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
GENRE_RULE_VERSION = "1.0.1"
GENRE_RULES = {
    "action": {
        "base_score": 0.3,
        "required": {
            # "condition_type": value
        },
        "boosts": [
            # ("condition_type", value, 0.1),
        ],
        "penalties": [
            # ("condition_type", value, 0.1),
        ]
    },
    "adult": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "adventure": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "fantasy": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "gender_bender": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "harem": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "martial_arts": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "romance": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "wuxia": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "xianxia": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "xuanhuan": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "yaoi": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
    "yuri": {
        "base_score": 0.3,
        "required": {},
        "boosts": [],
        "penalties": []
    },
}