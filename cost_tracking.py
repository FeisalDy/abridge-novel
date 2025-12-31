# cost_tracking.py
"""
Cost & Token Tracking for Abridge Pipeline

PURPOSE:
This module provides ACCOUNTING INSTRUMENTATION for tracking LLM usage
across the condensation pipeline. It records token counts and estimates
costs for each LLM call.

IMPORTANT DESIGN PRINCIPLES:
- Tracking is OBSERVATIONAL ONLY - it never blocks or modifies execution
- All events are persisted to SQLite for later analysis
- Historical data is NEVER overwritten (append-only)
- Tracking failures are logged but do NOT halt the pipeline
- This is accounting instrumentation, not optimization or budget enforcement

WHY THIS EXISTS:
LLM usage cost is non-trivial for large novels. Without tracking:
- Cost attribution is impossible
- Usage patterns cannot be analyzed
- Budgeting and planning is guesswork
This module provides the data foundation for cost visibility.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager

from guardrails import get_run_id, GUARDRAIL_DB_PATH


# --------------------------------------------------
# Configuration: Model Pricing
# --------------------------------------------------
# Pricing in USD per 1M tokens.
# These are ESTIMATES and should be updated as pricing changes.
# If a model is not listed, cost will be stored as NULL.
#
# Conservative assumption: use the higher of input/output pricing
# if separate pricing is not available.

MODEL_PRICING = {
    # OpenAI models (via GitHub Copilot)
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-5-mini": {"input": 0.15, "output": 0.60},  # Assumed similar to 4o-mini
    
    # Gemini models
    "models/gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "models/gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "models/gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    
    # Groq (various models)
    "qwen/qwen3-32b": {"input": 0.00, "output": 0.00},  # Free tier
    "llama-3.1-70b-versatile": {"input": 0.00, "output": 0.00},
    
    # Cerebras
    "qwen-3-32b": {"input": 0.00, "output": 0.00},  # Free tier
    
    # Local models (Ollama, vLLM) - no cost
    "llama3": {"input": 0.00, "output": 0.00},
    "Qwen/Qwen2.5-32B-Instruct": {"input": 0.00, "output": 0.00},
}

# Database uses same file as guardrails for simplicity
COST_DB_PATH = GUARDRAIL_DB_PATH


# --------------------------------------------------
# Data structures
# --------------------------------------------------

@dataclass
class LLMUsageEvent:
    """
    Represents a single LLM call with token usage and cost.
    
    This is the atomic unit of cost tracking.
    Each LLM invocation produces exactly one event.
    """
    run_id: str
    stage: str  # "chapter", "arc", "super-arc", etc.
    unit_id: str  # Identifier for the unit being condensed
    model: str  # Model name/identifier
    input_tokens: int
    output_tokens: int
    estimated_cost: Optional[float]  # USD, or None if pricing unavailable
    created_at: datetime


# --------------------------------------------------
# SQLite persistence
# --------------------------------------------------

def _get_db_connection() -> sqlite3.Connection:
    """
    Get a connection to the cost tracking database.
    Creates the table if it doesn't exist.
    Uses the same database file as guardrails.
    """
    conn = sqlite3.connect(COST_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            unit_id TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            estimated_cost REAL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    # Create index for efficient run-based queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_llm_usage_events_run_id 
        ON llm_usage_events(run_id)
    """)
    conn.commit()
    return conn


@contextmanager
def _db_context():
    """Context manager for database connections."""
    conn = _get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def persist_usage_event(event: LLMUsageEvent) -> None:
    """
    Persist an LLM usage event to SQLite.
    
    This is append-only - events are never modified or deleted.
    Each event represents a single LLM call.
    """
    with _db_context() as conn:
        conn.execute("""
            INSERT INTO llm_usage_events 
            (run_id, stage, unit_id, model, input_tokens, output_tokens, estimated_cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.run_id,
            event.stage,
            event.unit_id,
            event.model,
            event.input_tokens,
            event.output_tokens,
            event.estimated_cost,
            event.created_at.isoformat(),
        ))
        conn.commit()


# --------------------------------------------------
# Cost estimation
# --------------------------------------------------

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """
    Estimate the cost of an LLM call in USD.
    
    Returns None if pricing is not available for the model.
    Cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    
    CONSERVATIVE ASSUMPTION:
    If a model is not in the pricing table, we return None rather than
    guessing. This ensures cost reports are accurate, not misleading.
    """
    if model not in MODEL_PRICING:
        return None
    
    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens * pricing["input"]) / 1_000_000
    output_cost = (output_tokens * pricing["output"]) / 1_000_000
    
    return input_cost + output_cost


# --------------------------------------------------
# Core tracking function
# --------------------------------------------------

def record_llm_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    stage: str,
    unit_id: str,
) -> LLMUsageEvent:
    """
    Record an LLM usage event and persist it to the database.
    
    This is the main entry point for cost tracking.
    Call this AFTER each LLM call completes.
    
    Args:
        model: The model name/identifier used for the call
        input_tokens: Number of tokens in the input/prompt
        output_tokens: Number of tokens in the output/completion
        stage: The pipeline stage ("chapter", "arc", "super-arc", etc.)
        unit_id: Identifier for the unit (e.g., "chapter_001", "arc_01")
    
    Returns:
        The LLMUsageEvent that was recorded (for logging/inspection)
    
    IMPORTANT: This function NEVER raises exceptions that would halt the pipeline.
    Any errors are logged but swallowed to ensure tracking remains non-blocking.
    """
    try:
        # Estimate cost
        cost = estimate_cost(model, input_tokens, output_tokens)
        
        # Create event
        event = LLMUsageEvent(
            run_id=get_run_id(),
            stage=stage,
            unit_id=unit_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            created_at=datetime.utcnow(),
        )
        
        # Persist to database
        persist_usage_event(event)
        
        return event
        
    except Exception as e:
        # Tracking must NEVER halt the pipeline
        # Log the error but continue execution
        print(f"  ⚠️ Cost tracking error (non-blocking): {e}")
        # Return a dummy event to maintain interface contract
        return LLMUsageEvent(
            run_id=get_run_id(),
            stage=stage,
            unit_id=unit_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=None,
            created_at=datetime.utcnow(),
        )


# --------------------------------------------------
# Run summary
# --------------------------------------------------

def get_usage_summary(run_id: Optional[str] = None) -> dict:
    """
    Get a summary of LLM usage for a run.
    
    Args:
        run_id: The run to summarize. If None, uses current run.
    
    Returns:
        Dictionary with total tokens and estimated cost.
    """
    if run_id is None:
        run_id = get_run_id()
    
    with _db_context() as conn:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as call_count,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                SUM(estimated_cost) as total_cost
            FROM llm_usage_events
            WHERE run_id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        
        return {
            "run_id": run_id,
            "call_count": row[0] or 0,
            "total_input_tokens": row[1] or 0,
            "total_output_tokens": row[2] or 0,
            "total_cost": row[3],  # May be None if no pricing available
        }


def print_usage_summary(run_id: Optional[str] = None) -> None:
    """
    Print a human-readable summary of LLM usage for a run.
    
    This should be called at the end of pipeline execution to give
    operators visibility into LLM usage and costs.
    """
    summary = get_usage_summary(run_id)
    
    print("\n" + "-" * 50)
    print("LLM USAGE SUMMARY")
    print("-" * 50)
    print(f"Run ID: {summary['run_id']}")
    print(f"Total LLM calls: {summary['call_count']}")
    print(f"Total input tokens: {summary['total_input_tokens']:,}")
    print(f"Total output tokens: {summary['total_output_tokens']:,}")
    print(f"Total tokens: {summary['total_input_tokens'] + summary['total_output_tokens']:,}")
    
    if summary['total_cost'] is not None:
        print(f"Estimated cost: ${summary['total_cost']:.4f} USD")
    else:
        print("Estimated cost: N/A (pricing not available for all models)")
    
    print("-" * 50)
