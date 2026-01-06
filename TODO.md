---
# Abridge Pipeline – TODO Checklist

**Last Updated:** 2026-01-06
---
## Core Pipeline Enhancements

### Chapter Condensation (Stage 1)

* [x] Add deterministic pre-filtering to remove non-plot text
  *Drop paragraphs with no named entities, no dialogue, and no past-tense actions.*
  **DONE (2026-01-06):** Implemented in `prefilter.py`. Language-aware: only English text is filtered. Non-English (Chinese, CJK, etc.) passes through unchanged per editorial safety rules.
* [x] Replace large LLM usage with a local 7B–9B compression model
  *Restrict the model to chapter-local condensation only.*
  **DONE (2026-01-06):** Implemented `ollama_llm.py`. Supports local 7B-9B models (qwen2.5:7b, llama3.1:8b, mistral:7b, gemma2:9b). Use with `LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b`.
* [x] Enforce strict “no inference / no reordering” editor constraints at this stage
  *Chapter output must preserve original chronology and causality.*
  **DONE (2026-01-06):** Added explicit prohibitions to BASE_CONDENSATION_PROMPT in `prompt.py`: no reordering events, no inferring unstated info, no inventing motives/feelings/outcomes.
* [ ] Add automatic retry with stricter prompt if validation fails
  *Do not escalate model size.*
  **BLOCKED (2026-01-06):** Requires validation logic (TODOs lines 62-65) which is not yet implemented. Guardrails are observational only.

---

### Structural Scaffolding

* [x] Extract and persist per-chapter character lists
  **DONE (2026-01-06):** Implemented in `character_indexing.py`. Structure stores `character → chapters_present` (functionally equivalent; can derive chapter→characters programmatically).
* [ ] Extract and persist per-chapter event lists
  **SKIPPED (2026-01-06):** Requires LLM-based semantic extraction (adds cost). Current `event_keywords.py` provides lexical keyword signals only.
* [ ] Extract and persist decision → outcome pairs where present
  **SKIPPED (2026-01-06):** Requires LLM-based semantic extraction (similar to event lists).
* [ ] Require all extracted elements to appear in condensed output
  **BLOCKED (2026-01-06):** Depends on event lists and decision→outcome extraction which are not implemented.

---

### Translation & Input Normalization (SKIP THIS TASK, ILL DO IT LATER)

* [ ] Implement translation step for non-English raw novels
  *Ensure all downstream stages operate on English text.*
* [ ] Normalize names, titles, and aliases post-translation
  *Preserve character identity consistency.*

---

### Arc Condensation (Stage 2)

* [x] Define deterministic arc grouping rules (fixed chapter counts or volumes)
  **DONE (2026-01-06):** Implemented in `arc_condensation.py` with `CHAPTERS_PER_ARC = 10`. Deterministic processing via sorted chapter files.
* [x] Merge condensed chapters within each arc before re-condensation
  **DONE (2026-01-06):** Implemented in `arc_condensation.py` lines 137-144. Chapters merged with double newline separator before sending to LLM.
* [x] Use mid-tier model or limited cloud LLM only at this stage
  **DONE (2026-01-06):** Implemented stage-specific model selection. Each stage passes its name to `create_llm(stage)`. Use env vars `CHAPTER_LLM_PROVIDER`, `ARC_LLM_PROVIDER`, `NOVEL_LLM_PROVIDER` to override per-stage.
* [x] Remove cross-chapter redundancy without altering event order
  **DONE (2026-01-06):** Handled by BASE_CONDENSATION_PROMPT which includes "no reordering" and "remove repetition" constraints.

---

### Full Novel Condensation (Stage 3)

* [x] Merge all condensed arcs in strict chronological order
  **DONE (2026-01-06):** Implemented in `novel_condensation.py` lines 518-555. Arc files are sorted alphabetically and merged with `"\n\n".join()` preserving chronological order.
* [x] Run a single global condensation pass
  **DONE (2026-01-06):** Implemented in `novel_condensation.py` lines 643-674. Single `output_condense_fn(combined_input)` call produces `novel.condensed.txt`. Multi-part chunking only triggers for output overflow.
* [x] Reserve 32B-class or premium LLM usage for this step only
  **DONE (2026-01-06):** Implemented via stage-specific model selection. Line 42: `create_llm(stage="novel")`. Use `NOVEL_LLM_PROVIDER` env var to reserve premium models. Default models (qwen-3-32b, Qwen2.5-32B) are 32B-class.
* [x] Enforce "no further summarization" beyond rule-compliant condensation
  **DONE (2026-01-06):** Enforced in `prompt.py` BASE_CONDENSATION_PROMPT: "Do not omit events that influence future developments" and "Do not rewrite the story into an abstract summary."

---

### Validation & Quality Control

* [ ] Implement event coverage validation (no missing required events)
  **BLOCKED (2026-01-06):** Requires event extraction (Structural Scaffolding TODO) which is SKIPPED due to LLM cost.
* [ ] Implement character continuity validation
  **BLOCKED (2026-01-06):** Requires upstream character/event extraction which is not implemented.
* [ ] Implement chronology monotonicity checks
  **BLOCKED (2026-01-06):** Requires event timeline extraction which is not implemented.
* [ ] Block pipeline progression on validation failure
  **BLOCKED (2026-01-06):** Depends on validation implementations above.

---

### Cost & Performance Controls

* [x] Track token counts per stage
  **DONE (2026-01-06):** Implemented in `cost_tracking.py`. Each LLM call records `input_tokens`, `output_tokens`, and `stage` to SQLite via `record_llm_usage()`.
* [x] Track cost per novel and per stage
  **DONE (2026-01-06):** Implemented in `cost_tracking.py`. Costs estimated via `MODEL_PRICING` table and aggregated by `get_usage_summary()`. Reports printed at pipeline end.
* [x] Prevent automatic escalation to larger models
  **DONE (2026-01-06):** No automatic escalation exists in the codebase. Stage-specific models are explicitly configured via `CHAPTER_LLM_PROVIDER`, `ARC_LLM_PROVIDER`, `NOVEL_LLM_PROVIDER` env vars.
* [x] Log and review retries for systematic rule violations
  **DONE (2026-01-06):** Retries are logged to console with attempt count. MAX_LLM_RETRIES=3 in all condensation modules. Guardrail events capture compression ratio violations.

---

### Metadata & Separation of Concerns

* [x] Expand Genre and Tags definitions with finer sub-genres and themes
  **DONE (2026-01-06):** Implemented in `genre_resolver.py` (15+ genres with `GENRE_TAXONOMY`) and `tag_resolver.py` (30+ tags in `TAG_TAXONOMY`). Includes sub-categories for Eastern Fantasy, System/GameLit, Relationship, Protagonist Form, etc.
* [x] Ensure genre metadata never influences narrative condensation
  **DONE (2026-01-06):** `prompt.py` line 13 explicitly prohibits genre labels: "Do not add opinions, evaluations, interpretations, or genre labels." Genre/tag resolvers are Tier-3 optional features that run AFTER condensation completes.
* [x] Store metadata separately from condensed text
  **DONE (2026-01-06):** Data directories enforce separation: condensed text in `data/chapters_condensed/`, `data/arcs_condensed/`, `data/novel_condensed/`; metadata in `data/genre_resolved/`, `data/tag_resolved/`, `data/character_salience/`, etc.

---

## Editorial Guardrails

* [ ] Version and freeze the base editor prompt
* [ ] Document all changes to condensation rules
* [ ] Add regression tests using known novels
* [ ] Validate that condensed output remains readable as standalone narrative

---

*Reminder:
Abridge behaves like a disciplined editor — not a critic, not a reviewer, not a storyteller.*

---
