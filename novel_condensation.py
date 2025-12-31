import os
from prompt import BASE_CONDENSATION_PROMPT
from llm import create_llm
from utils import reduce_until_fit
from guardrails import record_condensation

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

def condense_text(text: str) -> str:
    """
    Apply the base condensation prompt to any text.
    
    This is the atomic condensation operation used at all hierarchy levels.
    The same prompt is applied whether condensing arcs, super-arcs, or
    the final novel.
    """
    prompt = BASE_CONDENSATION_PROMPT.format(
        INPUT_TEXT=text
    )
    return run_llm(prompt)


# Legacy alias for backward compatibility
condense_novel = condense_text


def process_novel(novel_name: str) -> None:
    """
    Produce the final condensed novel from arc-level outputs.
    
    SCALABILITY FIX:
    The original implementation assumed all condensed arcs could be merged
    and processed in a single LLM call. This fails for extremely large novels
    where the combined arc text exceeds the model's context window.
    
    The fix uses reduce_until_fit() which:
    1. Checks if the merged input fits within the token limit.
    2. If yes, performs a single condensation (original behavior preserved).
    3. If no, creates intermediate hierarchical layers by grouping arcs
       deterministically and condensing each group, then recursing.
    
    This maintains:
    - The same condensation prompt at all levels.
    - Deterministic, reproducible grouping (by position, not semantics).
    - Original behavior for small novels that already fit.
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

    # Load all condensed arc texts as separate units
    arc_texts = []
    for filename in arc_files:
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            arc_texts.append(f.read())

    # GUARDRAIL: Create callback for recording condensation metrics.
    # This wrapper adapts record_condensation to the callback signature expected by reduce_until_fit.
    def guardrail_callback(input_text: str, output_text: str, stage: str, unit_id: str) -> None:
        record_condensation(
            input_text=input_text,
            output_text=output_text,
            stage=stage,
            unit_id=unit_id,
        )

    # Use reduce_until_fit to handle arbitrary input sizes.
    # For small novels: behaves like original (single condensation pass).
    # For large novels: creates intermediate hierarchy layers as needed.
    condensed_novel = reduce_until_fit(
        units=arc_texts,
        condense_fn=condense_text,
        layer_name="arc",
        verbose=True,
        guardrail_callback=guardrail_callback,
    )

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
