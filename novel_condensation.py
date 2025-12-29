import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm

# --------------------------------------------------
# Configuration
# --------------------------------------------------

ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"


# --------------------------------------------------
# LLM setup
# --------------------------------------------------

llm = create_llm()


def run_llm(prompt: str) -> str:
    return llm.generate(prompt)


# --------------------------------------------------
# Core logic
# --------------------------------------------------

def condense_novel(text: str) -> str:
    """
    Apply the base condensation prompt to full arc-merged text.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text
    )
    return run_llm(prompt)


def process_novel(novel_name: str) -> None:
    """
    Produce the final condensed novel from arc-level outputs.
    """
    input_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    output_dir = os.path.join(NOVEL_CONDENSED_DIR, novel_name)

    if not os.path.isdir(input_dir):
        raise ValueError(f"Arc directory not found: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    arc_files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith(".condensed.txt")
    )

    if not arc_files:
        raise ValueError("No arc files found")

    print(f"Condensing full novel from {len(arc_files)} arcs...")

    merged_text_parts = []

    for filename in arc_files:
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            merged_text_parts.append(f.read())

    merged_text = "\n\n".join(merged_text_parts)

    condensed_novel = condense_novel(merged_text)

    output_path = os.path.join(output_dir, "novel.condensed.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(condensed_novel)

    print(f"Final condensed novel written to: {output_path}")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python novel_condensation.py <novel_name>")

    novel_name = sys.argv[1]
    process_novel(novel_name)
