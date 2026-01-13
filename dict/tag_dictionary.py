# Taxonomy version: tracks tag list source
# From: Feydar/novelupdates_tags (NovelUpdates tag taxonomy, curated)
TAG_TAXONOMY_VERSION = "1.0.0"

# Rule version: tracks rule logic changes
# Increment when rule definitions change
# v1.0.0: Actor-centric validation for marriage, betrayal
#         Added harem mutual exclusion penalty
#         New condition types: actor_event_match, harem_penalty
# v1.0.1: Completely revamp rules for better precision
TAG_RULE_VERSION = "1.0.1"

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
}