"""
Abridge Pipeline Orchestrator

Runs the full condensation pipeline in order:
1. Chapter condensation
2. Arc condensation
3. Novel condensation

Guardrails:
- Length ratio monitoring is active throughout the pipeline
- Results are persisted to SQLite for inspection
- Summary is printed at the end of each run
"""

from chapter_condensation import process_novel as condense_chapters
from arc_condensation import process_novel as condense_arcs
from novel_condensation import process_novel as condense_novel
from guardrails import start_run, end_run, print_run_summary


def run_pipeline(novel_name: str) -> None:
    # GUARDRAIL: Start a new run to track all condensation events.
    # Each run gets a unique ID for later inspection and regression analysis.
    run_id = start_run()
    print(f"=== Starting pipeline for novel: {novel_name} ===")
    print(f"Guardrail run ID: {run_id}")

    try:
        print("\n[1/3] Condensing chapters...")
        condense_chapters(novel_name)

        print("\n[2/3] Condensing arcs...")
        condense_arcs(novel_name)

        print("\n[3/3] Condensing full novel...")
        condense_novel(novel_name)

        print(f"\n=== Pipeline complete for novel: {novel_name} ===")
    finally:
        # GUARDRAIL: Always print summary and end run, even if pipeline fails.
        # This ensures partial run data is still visible for debugging.
        print_run_summary(run_id)
        end_run()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python run_pipeline.py <novel_name>")

    novel_name = sys.argv[1]
    run_pipeline(novel_name)
