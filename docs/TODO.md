---
# Abridge Pipeline – TODO Checklist

**Last Updated:** 2026-01-06
---
> **Design Principle**
> Abridge behaves like a disciplined editor —
> not a critic, not a reviewer, not a storyteller.

---

## Core Pipeline Enhancements

### Chapter Condensation (Stage 1)

* [X] Add deterministic pre-filtering to remove non-plot text*Drop paragraphs with no named entities, no dialogue, and no past-tense actions.***DONE (2026-01-06):** Implemented in `prefilter.py`.Language-aware: only English text is filtered. Non-English (Chinese, CJK, etc.) passes through unchanged per editorial safety rules.
* [X] Replace large LLM usage with a local 7B–9B compression model*Restrict the model to chapter-local condensation only.***DONE (2026-01-06):** Implemented `ollama_llm.py`.Supports local 7B–9B models (qwen2.5:7b, llama3.1:8b, mistral:7b, gemma2:9b).Use with `LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b`.
* [X] Enforce strict “no inference / no reordering” editor constraints*Chapter output must preserve original chronology and causality.***DONE (2026-01-06):** Added explicit prohibitions to `BASE_CONDENSATION_PROMPT` in `prompt.py`.
* [ ] Add automatic retry with stricter prompt if validation fails
  *Do not escalate model size.*
  **BLOCKED (2026-01-06):** Requires validation logic (see Validation & QC section).

---

## Structural Scaffolding

* [X] Extract and persist per-chapter character lists**DONE (2026-01-06):** Implemented in `character_indexing.py`.Structure stores `character → chapters_present`.
* [ ] Extract and persist per-chapter event lists**SKIPPED (2026-01-06):** Requires LLM-based semantic extraction (costly).Current `event_keywords.py` provides lexical signals only.
* [ ] Extract and persist decision → outcome pairs**SKIPPED (2026-01-06):** Requires semantic extraction.
* [ ] Require all extracted elements to appear in condensed output
  **BLOCKED:** Depends on event and decision extraction.

---

## Translation & Input Normalization

*(SKIP THIS TASK — handled later)*

* [ ] Implement translation step for non-English novels
* [ ] Normalize names, titles, and aliases post-translation

---

## Arc Condensation (Stage 2)

* [X] Define deterministic arc grouping rules**DONE (2026-01-06):** `CHAPTERS_PER_ARC = 10`.
* [X] Merge condensed chapters before re-condensation**DONE (2026-01-06):** Implemented in `arc_condensation.py`.
* [X] Use mid-tier or limited cloud LLM only at this stage**DONE (2026-01-06):** Stage-specific model routing via `create_llm(stage)`.
* [X] Remove cross-chapter redundancy without altering order
  **DONE (2026-01-06):** Enforced via base prompt constraints.

---

## Full Novel Condensation (Stage 3)

* [X] Merge all arcs in strict chronological order**DONE (2026-01-06):** Alphabetical arc merge preserves order.
* [X] Run a single global condensation pass**DONE (2026-01-06):** Produces `novel.condensed.txt`.
* [X] Reserve 32B-class or premium LLMs for this step only**DONE (2026-01-06):** Controlled via `NOVEL_LLM_PROVIDER`.
* [X] Enforce “no further summarization” rule
  **DONE (2026-01-06):** Explicitly stated in base prompt.

---

## Validation & Quality Control

* [ ] Implement event coverage validation**BLOCKED:** Requires event extraction.
* [ ] Implement character continuity validation**BLOCKED:** Requires upstream extraction.
* [ ] Implement chronology monotonicity checks**BLOCKED:** Requires event timeline extraction.
* [ ] Block pipeline progression on validation failure**BLOCKED:** Depends on above validators.
* [ ] Integrate genre/tag consistency audit into final QA report
  **BLOCKED:** Depends on Feature 3.4c.
  *Audit results are advisory only and must NOT block pipeline progression.*

---

## Cost & Performance Controls

* [X] Track token counts per stage**DONE (2026-01-06):** Implemented in `cost_tracking.py`.
* [X] Track cost per novel and per stage**DONE (2026-01-06):** Aggregated via SQLite.
* [X] Prevent automatic escalation to larger models**DONE (2026-01-06):** Explicit per-stage configuration only.
* [X] Log and review retries for rule violations
  **DONE (2026-01-06):** MAX_LLM_RETRIES=3.

---

## Metadata & Separation of Concerns

> **Note:**
> Genre and Tag Resolution are Feature **3.4a (Genres)** and **3.4b (Tags)**.
> Any LLM involvement occurs **after resolution** and is strictly non-authoritative.

### Feature 3.4a – Genre Resolution

* [X] Expand genre taxonomy with sub-genres and themes
  **DONE (2026-01-06):** Implemented in `genre_resolver.py`.

### Feature 3.4b – Tag Resolution

* [X] Expand tag taxonomy (themes, mechanics, tropes)
  **DONE (2026-01-06):** Implemented in `tag_resolver.py`.

### Feature 3.4c – Genre & Tag Validation (Tier 4, Advisory)

* [ ] Implement LLM-based genre/tag consistency audit*LLM validates whether resolved genres/tags are supported by artifacts.*

  **Inputs (restricted):**

  - Resolved genres/tags (3.4a / 3.4b output)
  - Keyword frequency summaries
  - Event keyword signals
  - Character index summaries

  **LLM must NOT:**

  - Add new genres or tags
  - Remove or override resolved labels
  - Infer events not present in artifacts
  - Read raw novel text
* [ ] Emit support-strength annotations*Supported / Weak / Unsupported, with cited evidence.*
* [ ] Flag overstated or misleading labels*Warnings only.*
* [ ] Store validation output separately`data/genre_validation/`, `data/tag_validation/`
* [ ] Version validator prompts and schemas independently

---

## Editorial Guardrails

* [ ] Version and freeze the base editor prompt
* [ ] Document all rule changes
* [ ] Add regression tests using known novels
* [ ] Validate that condensed output reads as a standalone narrative

---

## Terminology Constraints

- **Resolution** determines labels (deterministic).
- **Validation** audits evidence support (LLM-assisted).
- Validation output is advisory, never authoritative.

---

*Reminder:*
Abridge behaves like a disciplined editor —
not a critic, not a reviewer, not a storyteller.
