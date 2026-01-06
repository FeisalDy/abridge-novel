---
# Abridge Pipeline – TODO Checklist

**Last Updated:** 2026-01-06
---
## Core Pipeline Enhancements

### Chapter Condensation (Stage 1)

* [x] Add deterministic pre-filtering to remove non-plot text
  *Drop paragraphs with no named entities, no dialogue, and no past-tense actions.*
  **DONE (2026-01-06):** Implemented in `prefilter.py`. Language-aware: only English text is filtered. Non-English (Chinese, CJK, etc.) passes through unchanged per editorial safety rules.
* [ ] Replace large LLM usage with a local 7B–9B compression model
  *Restrict the model to chapter-local condensation only.*
* [ ] Enforce strict “no inference / no reordering” editor constraints at this stage
  *Chapter output must preserve original chronology and causality.*
* [ ] Add automatic retry with stricter prompt if validation fails
  *Do not escalate model size.*

---

### Structural Scaffolding

* [ ] Extract and persist per-chapter character lists
* [ ] Extract and persist per-chapter event lists
* [ ] Extract and persist decision → outcome pairs where present
* [ ] Require all extracted elements to appear in condensed output

---

### Translation & Input Normalization (SKIP THIS TASK, ILL DO IT LATER)

* [ ] Implement translation step for non-English raw novels
  *Ensure all downstream stages operate on English text.*
* [ ] Normalize names, titles, and aliases post-translation
  *Preserve character identity consistency.*

---

### Arc Condensation (Stage 2)

* [ ] Define deterministic arc grouping rules (fixed chapter counts or volumes)
* [ ] Merge condensed chapters within each arc before re-condensation
* [ ] Use mid-tier model or limited cloud LLM only at this stage
* [ ] Remove cross-chapter redundancy without altering event order

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
