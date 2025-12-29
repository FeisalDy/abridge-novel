"""
    TODO: Refactor this docstring by following the PEP 257 standard
    chapter_condensation.py is responsible for turning raw novel chapters into condensed chapters,
    faithfully and deterministically, using the base condensation prompt.

    Responsibilities:
    1. Input Handling
        - Load raw chapter text files
        - Preserve chapter order
        - Treat each chapter as an independent unit
    2. Condensation Execution
        - Inject each chapter’s text into BASE_CONDENSATION_PROMPT
        - Send the prompt to the LLM
        - Receive the condensed output
    3. Output Handling
        - Save each condensed chapter as a separate file
        - Ensure outputs correspond 1:1 with inputs
        - Never overwrite raw chapter files
    4. Determinism & Repeatability
        - Given the same input and prompt version, behavior should be reproducible
        - Output order must match input order

    Non-Responsibilities:
    1. Structural Interpretation
        - Detect scenes
        - Detect story arcs
        - Reorder content
        - Merge chapters
    2. Semantic Interpretation
        - Judge importance
        - Decide what is “major” or “minor”
        - Add opinions or commentary
        - Inject genre or metadata
    3. Post Processing Intelligence
        - No validation of plot completeness
        - No consistency checking
        - No character tracking
        - No summarization of summaries
    4. Pipeline Progression
        - It must not trigger arc condensation
        - It must not handle multi-stage logic
        - It must not coordinate later steps
    5. UI/UX Considerations
        - No interactive interface
        - No progress bars (optional logging is fine)
        - No user-facing configuration logic

    Error Handling Scope
        - May fail loudly if input is invalid
        - May retry or log LLM failures
        - Must not attempt semantic recovery
    If condensation fails, the chapter fails — it is not silently skipped.

    Think this module as a conveyor belt that takes in raw chapters and produces edited chapters,
    without understanding the story beyond what the editor prompt enforces.
"""
import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm

# --------------------------------------------------
# Configuration
# --------------------------------------------------

llm = create_llm()

RAW_BASE_DIR = "data/raw"
OUTPUT_BASE_DIR = "data/chapters_condensed"

def run_llm(prompt: str) -> str:
    return llm.generate(prompt)


# --------------------------------------------------
# Core logic
# --------------------------------------------------

def condense_chapter(chapter_text: str) -> str:
    """
    Apply the base condensation prompt to a single chapter.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=chapter_text
    )
    return run_llm(prompt)


def process_novel(novel_name: str) -> None:
    """
    Condense all chapters of a novel.
    """
    raw_dir = os.path.join(RAW_BASE_DIR, novel_name)
    output_dir = os.path.join(OUTPUT_BASE_DIR, novel_name)

    if not os.path.isdir(raw_dir):
        raise ValueError(f"Raw novel directory not found: {raw_dir}")

    os.makedirs(output_dir, exist_ok=True)

    chapters = sorted(
        f for f in os.listdir(raw_dir)
        if f.endswith(".txt")
    )

    if not chapters:
        raise ValueError("No chapter files found")

    for filename in chapters:
        input_path = os.path.join(raw_dir, filename)
        output_filename = filename.replace(".txt", ".condensed.txt")
        output_path = os.path.join(output_dir, output_filename)

        print(f"Condensing {filename}...")

        with open(input_path, "r", encoding="utf-8") as f:
            chapter_text = f.read()

        condensed_text = condense_chapter(chapter_text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(condensed_text)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python chapter_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)