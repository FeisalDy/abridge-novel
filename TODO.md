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

* [ ] Merge all condensed arcs in strict chronological order
* [ ] Run a single global condensation pass
* [ ] Reserve 32B-class or premium LLM usage for this step only
* [ ] Enforce “no further summarization” beyond rule-compliant condensation

---

### Validation & Quality Control

* [ ] Implement event coverage validation (no missing required events)
* [ ] Implement character continuity validation
* [ ] Implement chronology monotonicity checks
* [ ] Block pipeline progression on validation failure

---

### Cost & Performance Controls

* [ ] Track token counts per stage
* [ ] Track cost per novel and per stage
* [ ] Prevent automatic escalation to larger models
* [ ] Log and review retries for systematic rule violations

---

### Metadata & Separation of Concerns

* [ ] Expand Genre and Tags definitions with finer sub-genres and themes
* [ ] Ensure genre metadata never influences narrative condensation
* [ ] Store metadata separately from condensed text

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
