"""
Abridge Pipeline Orchestrator

Runs the full condensation pipeline in order:
1. Chapter condensation
2. Arc condensation
3. Novel condensation
"""

from chapter_condensation import process_novel as condense_chapters
from arc_condensation import process_novel as condense_arcs
from novel_condensation import process_novel as condense_novel


def run_pipeline(novel_name: str) -> None:
    print(f"=== Starting pipeline for novel: {novel_name} ===")

    print("\n[1/3] Condensing chapters...")
    condense_chapters(novel_name)

    print("\n[2/3] Condensing arcs...")
    condense_arcs(novel_name)

    print("\n[3/3] Condensing full novel...")
    condense_novel(novel_name)

    print(f"\n=== Pipeline complete for novel: {novel_name} ===")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python run_pipeline.py <novel_name>")

    novel_name = sys.argv[1]
    run_pipeline(novel_name)
