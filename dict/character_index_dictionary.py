# ============================================================
# NAME FILTERING RULES
# ============================================================
#
# This file defines TWO different word filters used during
# character surface indexing.
#
# These rules are STRUCTURAL and DETERMINISTIC.
# They are NOT semantic and NOT narrative-aware.
#
# ------------------------------------------------------------
# 1. EXCLUDED_WORDS
# ------------------------------------------------------------
#
# PURPOSE:
#   Prevent false character entries caused by capitalized
#   words that are NOT reliable standalone names.
#
# HARD RULES — a word MUST be in EXCLUDED_WORDS if:
#
#   - It is frequently capitalized
#   - It is NOT a person by itself
#   - It CAN appear inside a valid name phrase
#   - It SHOULD NOT appear alone as a character entry
#
# EXCLUDED_WORDS ARE REMOVED ONLY WHEN STANDALONE.
#
# They DO NOT block multi-word names.
#
# Example (CORRECT behavior):
#   ❌ "Great"           -> removed
#   ❌ "Blood"           -> removed
#   ✅ "The Great Li"    -> kept
#   ✅ "Blood Emperor"  -> kept
#
# MUST GO INTO EXCLUDED_WORDS:
#   - Articles (The, A, An)
#   - Titles & ranks (King, Emperor, Lord)
#   - Honorifics (Divine, Grand, Sacred)
#   - Directions (North, South)
#   - Institutions (Sect, Hall, Palace)
#   - Abstract adjectives used as modifiers
#
# NEVER PUT INTO EXCLUDED_WORDS:
#   - Verbs
#   - Logical connectors
#   - Sentence organizers
#   - Discourse markers
#
# ------------------------------------------------------------
# 2. DISCOURSE_WORDS
# ------------------------------------------------------------
#
# PURPOSE:
#   Remove sentence-level words that leak into name extraction
#   due to capitalization at sentence boundaries.
#
# HARD RULES — a word MUST be in DISCOURSE_WORDS if ALL apply:
#
#   - Removing it does NOT change sentence meaning
#   - It NEVER refers to a person, place, sect, or title
#   - It NEVER appears inside a valid name phrase
#   - It ONLY organizes discourse or narration flow
#
# DISCOURSE_WORDS ARE NEVER PART OF NAMES.
#
# Example (CORRECT behavior):
#   ❌ "However"   -> removed
#   ❌ "Meanwhile" -> removed
#   ❌ "Suddenly"  -> removed
#
# MUST GO INTO DISCOURSE_WORDS:
#   - Discourse markers (However, Therefore)
#   - Temporal connectors (Meanwhile, Suddenly)
#   - Narrative transitions (Finally, Eventually)
#
# NEVER PUT INTO DISCOURSE_WORDS:
#   - Articles (The)
#   - Titles (Great, Divine)
#   - Ranks (King, Emperor)
#   - Nouns that could appear inside names
#
# ------------------------------------------------------------
# QUICK DECISION RULE
# ------------------------------------------------------------
#
# Ask this ONE question:
#
#   "Could this word ever appear inside a character name?"
#
#   YES  -> EXCLUDED_WORDS (if unreliable alone)
#   NO   -> DISCOURSE_WORDS
#
# If unsure: DO NOT add it anywhere.
#
# False negatives are acceptable.
# False positives are NOT.
#
# ============================================================

DISCOURSE_WORDS = frozenset({
    # Contrast / concession
    "However", "Nonetheless", "Nevertheless", "Still", "Yet", "Though", "Although",
    "Instead", "Otherwise", "Rather",

    # Cause / effect
    "Therefore", "Thus", "Hence", "Consequently", "Accordingly",

    # Addition / emphasis
    "Moreover", "Furthermore", "Additionally", "Likewise", "Similarly",

    # Time / progression
    "Meanwhile", "Afterward", "Afterwards", "Beforehand", "Eventually",
    "Finally", "Initially", "Previously", "Subsequently", "Ultimately",

    # Sudden action markers
    "Suddenly", "Abruptly", "Instantly", "Immediately",

    # Clarification / framing
    "Indeed", "Instead", "Otherwise", "Specifically", "Generally",

    # Narrative flow fillers
    "Then", "Now", "Hereafter",

    # Edge-case discourse starters (verified non-entity)
    "Otherwise", "Altogether", "Overall", "Looking", "Seeing", "Soon",
    "Thinking", "Such", "Immediately", "Instead", "Otherwise", "Whether",
    "Hearing", "Without", "Perhaps", "Especially", "Compared", "Anyway",
    "Inside", "Moreover", "Could", "Okay", "Maybe", "Regarding", "Almost",
    "Taking", "Wait", "Until", "Based", "Obviously", "According", "Considering",
    "Fortunately", "Sadly", "Like", "Either", "Come", "Take", "Thank", "Gradually",
    "Please", "Rumble", "Recalling", "Including", "Crack", "Afterwards", "Unknowingly",
    "Having", "Everything", "Make", "More", "Using", "Unless", "There", "Gender",
    "Judging", "Unexpectedly", "Naturally", "Standing", "More", "Think",
    "Forget", "Relying", "Originally", "Completely", "Dantian", "Have", "Once", "Everyone",
    "Immortality", "Kingdom", "Academy", "Combined", "Boom", "Various", "Faintly",
    "Feeling", "Sure", "Listening", "Tell", "Unconsciously", "Witnessing", "Want", "Walking", "Subconsciously", "Sitting",
    "Returning", "Report", "Pass", "Other", "Observe", "Name", "Listen", "Less", "Internet",
    "Humph", "Densely", "Choose", "Behind", "Authority", "Anyone", "Ahhhhh", "Would", "Prevent", "Refining",
    "Revealing", "Knowing", "Holding", "Find", "About", "Actually", "Ahem", "Another", "Apart", "Arriving",
    "Back", "Besides", "Boring", "Brush", "Caught", "Click", "Coming", "Cooperation", "Cough", "Definitely",
    "Despite", "Differently", "Does", "Early", "Ever", "Except", "Excuse", "Familiar", "Follow",
    "Found", "Friends", "Fuck", "Give", "Going", "Guess", "Haha", "Hahahaha", "Hehe", "Hehehe", "Hello",
    "Here", "Hiss", "Hmph", "Hold", "Hurry", "Impossible", "Interesting", "Interrogation", "Keep", "Leave",
    "Leaving", "Look", "Meeting", "Morning", "Nonsense", "Normally", "Oops", "Others", "Outside", "People",
    "Phew", "Probably", "Quick", "Quickly", "Realizing", "Really", "Regardless", "Remember", "Rescue",
    "Return", "Right", "Send", "Shall", "Should", "Shouldn", "Sighing", "Somewhere", "Sorry", "Speaking",
    "Squeak", "Stop", "Sunlight", "Thanks", "Turning", "Understood", "Unfortunately", "Unlike", "Very",
    "Visiting", "Welcome", "Well", "Whatever", "Whouldn", "Yeah", "Didn", "Different", "Directly", "Doesn",
    "Ouch",
})


EXCLUDED_WORDS = frozenset({
    # ── Articles / Determiners ─────────────────────────────
    "The", "A", "An", "This", "That", "These", "Those",
    "Each", "Every", "Either", "Neither", "Some", "Any",
    "All", "Both", "Few", "Many", "Several", "Most", "As",

    # ── Pronouns / Possessives ─────────────────────────────
    "I", "You", "He", "She", "It", "We", "They",
    "Me", "Him", "Her", "Us", "Them",
    "My", "Your", "His", "Her", "Its", "Our", "Their",

    # ── Question / Relative Words ──────────────────────────
    "Who", "Whom", "Whose", "Which", "What",
    "When", "Where", "Why", "How", "Whether",

    # ── Conjunctions / Logical Glue ────────────────────────
    "And", "Or", "But", "So", "Yet", "For", "Nor",
    "If", "Then", "Else", "Although", "Because", "Unless",
    "While", "Whereas", "Since", "Until",

    # ── Prepositions ──────────────────────────────────────
    "In", "On", "At", "By", "To", "From", "Of", "With",
    "Without", "Within", "Through", "Across", "Along",
    "Among", "Between", "Beyond", "Over", "Under",
    "Above", "Below", "Upon", "Against", "Around",

    # ── Temporal / Ordering Words ─────────────────────────
    "Before", "After", "During", "Meanwhile",
    "Now", "Then", "Later", "Earlier",
    "Today", "Tomorrow", "Yesterday",
    "First", "Second", "Third", "Next", "Last", "Final",

    # ── Numerals / Quantifiers ────────────────────────────
    "One", "Two", "Three", "Four", "Five", "Six",
    "Seven", "Eight", "Nine", "Ten",
    "Hundred", "Thousand", "Million", "Billion",

    # ── Meta / Structural Words ───────────────────────────
    "Chapter", "Chapters", "Part", "Parts", "Section",
    "Book", "Volume", "Arc", "Episode", "Page",

    # ── Generic Titles (NOT identity alone) ───────────────
    "Master", "Lord", "Lady", "Sir", "Madam",
    "Elder", "Senior", "Junior",
    "Young", "Old", "Grand", "Great", "Divine",
    "Queen", "King", "Prince", "Princess",
    "Emperor", "Empress", "Duke", "Duchess",
    "Baron", "Baroness", "Count", "Countess",
    "General", "Captain", "Commander", "Soldier",
    "Miss", "Mister", "Mr", "Mrs", "Ms", "Dr",
    "Professor", "Teacher", "Student", "Disciple",
    "Venerable",

    # ── Directions / Generic Locations ────────────────────
    "North", "South", "East", "West", "Central",
    "Upper", "Lower", "Inner", "Outer",

    # ── Generic Places (too broad to be names alone) ──────
    "Mountain", "Mountains", "River", "Rivers",
    "Valley", "Palace", "Hall", "Sect", "Clan",
    "City", "Town", "Village", "Region", "Realm",
    "Mansion", "Dynasty", "Kingdom", "Empire",

    # ── Generic Adjectives (capitalization noise) ─────────
    "Good", "Evil", "True", "False", "Real",
    "Pure", "Dark", "Light", "Black", "White",
    "Strong", "Weak", "High", "Low", "Deep", "Shallow",
    "Long", "Short", "Wide", "Narrow",

    # ── Disallowed Narrative Fillers ──────────────────────
    "Still", "Just", "Only", "Even", "Also",
    "Already", "Almost", "Nearly", "Rather",

    # ── Hard rejects (common MT artifacts) ────────────────
    "Being", "Having", "Doing", "Making",
    "Something", "Someone", "Everything", "Nothing",
    "Time", "Little", "Song", "Secret", "Void", "Space",
    "Cosmos", "Universe", "World", "Life", "Death", "Earth",
    "Transform", "Human", "Faced", "Destiny", "Virtual", "Transforming",
    "Things", "Tenacity", "Alas", "Annihilation", "Believe", "Call", "Cold",
    "Countless", "Crash", "Creation", "Damn", "Dang", "Deputy", "Fifteen", "Fifty",
    "Forest", "Gate", "Half", "Illusion", "Karma", "Kill", "Knowledge", "Magic", "Netherworld",
    "Ordinary", "Pope", "President", "Revelation", "Saint", "Seeing", "Seventh", "Sister", "Sixteen",
    "Staff", "Steel", "Tower", "Venom", "Warcraft", "Witch", "Crusaders", "Goddess", "Grandpa", "Paladin",
    "Seventeen",
})
