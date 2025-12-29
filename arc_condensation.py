import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm

# --------------------------------------------------
# Configuration
# --------------------------------------------------

CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"
ARCS_CONDENSED_DIR = "data/arcs_condensed"

CHAPTERS_PER_ARC = 10


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm()


def run_llm(prompt: str) -> str:
    return llm.generate(prompt)


# --------------------------------------------------
# Core logic
# --------------------------------------------------

def condense_arc(text: str) -> str:
    """
    Apply the base condensation prompt to merged chapter text.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text
    )
    return run_llm(prompt)


def process_novel(novel_name: str) -> None:
    """
    Condense chapter-level outputs into arc-level outputs.
    """
    input_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)

    if not os.path.isdir(input_dir):
        raise ValueError(f"Condensed chapters directory not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    chapter_files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".condensed.txt")
    )

    if not chapter_files:
        raise ValueError("No condensed chapter files found")

    arc_index = 1

    for i in range(0, len(chapter_files), CHAPTERS_PER_ARC):
        arc_chapters = chapter_files[i:i + CHAPTERS_PER_ARC]

        print(f"Condensing arc {arc_index} ({len(arc_chapters)} chapters)...")

        merged_text_parts = []

        for filename in arc_chapters:
            path = os.path.join(input_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                merged_text_parts.append(f.read())

        merged_text = "\n\n".join(merged_text_parts)

        condensed_arc = condense_arc(merged_text)

        output_filename = f"arc_{arc_index:02d}.condensed.txt"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(condensed_arc)

        arc_index += 1


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python arc_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)
