# Novel Condensation Project Plan

## 1. Project Goal

The goal of this project is to create a system that takes a complete novel
(including very long novels with millions of words) and produces a faithful,
objective, long-form condensed version of the entire story.

The condensed output should be approximately 10,000–50,000 words and preserve
the full plot, allowing a reader to quickly decide whether the novel is worth
reading in full.

The system must not judge, rate, review, or interpret the novel. The final
decision is always made by the reader.

---

## 2. Core Principles

### 2.1 Condense, Do Not Summarize
- Preserve all plot events and actions
- Preserve causality and chronological order
- Remove redundancy, filler, and padding
- Avoid abstract summaries or high-level descriptions

### 2.2 Objectivity First
- No genre labels during condensation
- No opinions or evaluations
- No interpretation of themes or meaning
- No determination of what is “important”

### 2.3 Reader-Centered Outcome
- The condensed novel exists to support human judgment
- The system does not decide quality or value

---

## 3. High-Level Workflow

### Phase 1: Input Preparation
- Accept the complete novel as input
- Preserve original chapters or scenes if available
- Otherwise, infer reasonable narrative boundaries

Purpose: Respect the novel’s original structure.

---

### Phase 2: Scene-Level Condensation
Each scene or small narrative unit is rewritten to:
- Remove repetitive descriptions
- Remove prolonged padding
- Preserve all character actions and decisions
- Preserve consequences and outcomes
- Maintain chronological order

Purpose: Produce a shorter but complete version of every scene.

---

### Phase 3: Chapter-Level Consolidation
Condensed scenes within a chapter are merged into a single coherent narrative.

Requirements:
- Logical flow
- Clear transitions
- No loss of causal links

Purpose: Create concise but readable chapter narratives.

---

### Phase 4: Arc-Level Consolidation
Chapters are grouped into narrative arcs based on:
- Goals
- Conflicts
- Locations
- Time periods

Each arc is further condensed while preserving:
- Plot progression
- Character development
- Narrative continuity

Purpose: Remove large-scale repetition without losing story structure.

---

### Phase 5: Full-Novel Condensed Output
All condensed arcs are merged into a single continuous narrative.

Requirements:
- Target length of 10,000–50,000 words
- Clear chronology
- Consistent character identities
- No missing plot transitions

Purpose: Produce an abridged novel that can be read quickly.

---

## 4. Genre Detection (Optional Feature)

Genre detection is a secondary feature and must be separate from condensation.

Rules:
- Performed only after the condensed novel is created
- Presented as metadata, not embedded in the narrative
- Based on explicit plot facts

Genre information must never influence the condensed text itself.

---

## 5. Output Design

### 5.1 Primary Output
- A continuous condensed novel narrative
- No labels, opinions, or evaluations
- Intended to be read like a short novel

### 5.2 Optional Metadata
- Detected genres
- Character list
- Timeline overview

Metadata should be clearly separated and optional.

---

## 6. Success Criteria

The project is successful if:
- The full plot can be understood from the condensed version
- The reader can decide whether to read the original novel
- The condensed text feels faithful and coherent
- No subjective judgment is imposed by the system

---

## 7. Explicit Non-Goals

The system will not:
- Judge writing quality
- Score or rank novels
- Replace reading the original work
- Interpret symbolism or themes
- Enforce genre expectations
****