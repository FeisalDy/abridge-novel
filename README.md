# Abridge

Abridge is a project focused on **faithful, objective condensation of full-length novels**.

The goal is to take very long novels (including million-word works) and produce a **long-form condensed version** that preserves the entire plot, chronology, and causality, allowing a reader to decide whether the original novel is worth reading.

This project does **not** judge, rate, or review novels.
It does **not** attempt literary criticism or subjective evaluation.

The condensed output is intended to function like an abridged edition:
shorter, faster to read, but faithful to the original story.

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure LLM Provider

The project supports three LLM providers: OpenAI, Google Gemini, and Ollama.

Edit `llm/llm_config.py` to set your preferred provider:

```python
LLM_PROVIDER = "openai"  # Options: "openai", "gemini", "ollama"
```

### 3. Set API Keys

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**For Google Gemini:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**For Ollama:**
- Install Ollama locally: https://ollama.ai
- Start the Ollama service (usually runs on `http://localhost:11434`)
- Pull a model: `ollama pull llama3`
- No API key needed

### 4. Test the Setup

```bash
python test_imports.py
```

---

## Project Status

This repository currently contains the project plan and LLM infrastructure.

See [`PLAN.md`](1. PLAN.md) for the full design philosophy and workflow.

Implementation is in progress.
