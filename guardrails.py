# guardrails.py
"""
Length Ratio Guardrails for Abridge Pipeline

PURPOSE:
This module provides SAFETY INSTRUMENTATION for detecting suspicious
condensation behavior. It measures input/output length ratios and flags
abnormal compression that may indicate narrative loss.

IMPORTANT DESIGN PRINCIPLES:
- Guardrails are OBSERVATIONAL ONLY - they never block or modify output
- All events are persisted to SQLite for later analysis and regression testing
- Historical data is NEVER overwritten (append-only)
- This is safety instrumentation, not quality improvement

WHY THIS EXISTS:
Condensation failures are usually silent. A model might:
- Over-condense (ratio too low) → narrative loss
- Under-condense (ratio too high) → insufficient compression
Without measurement, these failures go unnoticed until human review.
"""

import os
import sqlite3
import uuid
from typing import Optional, Literal
from dataclasses import dataclass
from contextlib import contextmanager
from dotenv import load_dotenv
from datetime import datetime, timezone
load_dotenv()
# --------------------------------------------------
# Configuration: Compression Ratio Thresholds
# --------------------------------------------------
# These thresholds are CONSERVATIVE defaults based on expected condensation behavior.
# They can be tuned based on observed data without changing pipeline logic.
#
# Ratio = output_length / input_length
# - Low ratio (< expected) → aggressive condensation, possible narrative loss
# - High ratio (> expected) → insufficient condensation, may indicate model issues

# Chapter-level thresholds (depth=0)
# Chapters condense raw text; expect moderate compression.
CHAPTER_GREEN_MIN = 0.40
CHAPTER_GREEN_MAX = 0.70
CHAPTER_YELLOW_MIN = 0.30  # Below this is RED
CHAPTER_YELLOW_MAX = 0.85  # Above this is RED

# Arc and higher-level thresholds (depth>=1)
# Higher levels condense already-condensed text; expect more aggressive compression.
ARC_GREEN_MIN = 0.25
ARC_GREEN_MAX = 0.50
ARC_YELLOW_MIN = 0.15  # Below this is RED
ARC_YELLOW_MAX = 0.65  # Above this is RED

# Database configuration
GUARDRAIL_DB_PATH = os.getenv("GUARDRAIL_DB_PATH", "abridge_guardrails.db")

# Status type
StatusType = Literal["green", "yellow", "red"]


# --------------------------------------------------
# Data structures
# --------------------------------------------------

@dataclass
class GuardrailEvent:
    """
    Represents a single condensation measurement event.
    
    This is the atomic unit of guardrail observation.
    Each condensation operation produces exactly one event.
    """
    run_id: str
    stage: str  # "chapter", "arc", "super-arc", etc.
    unit_id: str  # Identifier for the unit being condensed
    input_length: int  # Token count (or character count as fallback)
    output_length: int
    ratio: float  # output_length / input_length
    status: StatusType
    created_at: datetime


# --------------------------------------------------
# Run context management
# --------------------------------------------------

# Global run context - set once per pipeline execution
_current_run_id: Optional[str] = None


def start_run() -> str:
    """
    Start a new guardrail run and return the run_id.
    
    This should be called once at the beginning of pipeline execution.
    All subsequent guardrail events will be associated with this run_id.
    """
    global _current_run_id
    _current_run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    return _current_run_id


def get_run_id() -> str:
    """
    Get the current run_id, starting a new run if needed.
    """
    global _current_run_id
    if _current_run_id is None:
        return start_run()
    return _current_run_id


def end_run() -> None:
    """
    End the current run and reset the run_id.
    
    This should be called at the end of pipeline execution.
    """
    global _current_run_id
    _current_run_id = None


# --------------------------------------------------
# Threshold classification
# --------------------------------------------------

def get_thresholds_for_stage(stage: str) -> tuple[float, float, float, float]:
    """
    Get compression ratio thresholds based on stage/depth.
    
    Stages starting with "chapter" use chapter-level thresholds.
    All other stages (arc, super-arc, super-super-arc, etc.) use arc-level thresholds.
    
    Returns: (green_min, green_max, yellow_min, yellow_max)
    """
    # Chapter-level uses more lenient thresholds (condensing raw text)
    if stage.lower().startswith("chapter"):
        return (CHAPTER_GREEN_MIN, CHAPTER_GREEN_MAX, 
                CHAPTER_YELLOW_MIN, CHAPTER_YELLOW_MAX)
    
    # Arc and all higher levels use tighter thresholds (condensing condensed text)
    return (ARC_GREEN_MIN, ARC_GREEN_MAX, 
            ARC_YELLOW_MIN, ARC_YELLOW_MAX)


def classify_ratio(ratio: float, stage: str) -> StatusType:
    """
    Classify a compression ratio into GREEN, YELLOW, or RED.
    
    Classification logic:
    - GREEN: ratio is within expected healthy range
    - YELLOW: ratio is borderline, review recommended
    - RED: ratio indicates likely narrative loss or model failure
    
    This function ONLY classifies - it does not take any action.
    """
    green_min, green_max, yellow_min, yellow_max = get_thresholds_for_stage(stage)
    
    # GREEN: within expected range
    if green_min <= ratio <= green_max:
        return "green"
    
    # YELLOW: borderline (between yellow threshold and green boundary)
    if yellow_min <= ratio < green_min or green_max < ratio <= yellow_max:
        return "yellow"
    
    # RED: outside acceptable range
    return "red"


# --------------------------------------------------
# SQLite persistence
# --------------------------------------------------

def _get_db_connection() -> sqlite3.Connection:
    """
    Get a connection to the guardrails database.
    Creates the database and table if they don't exist.
    """
    conn = sqlite3.connect(GUARDRAIL_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guardrail_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            unit_id TEXT NOT NULL,
            input_length INTEGER NOT NULL,
            output_length INTEGER NOT NULL,
            ratio REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    # Create index for efficient run-based queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_guardrail_events_run_id 
        ON guardrail_events(run_id)
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


def persist_event(event: GuardrailEvent) -> None:
    """
    Persist a guardrail event to SQLite.
    
    This is append-only - events are never modified or deleted.
    Each event represents a single condensation measurement.
    """
    with _db_context() as conn:
        conn.execute("""
            INSERT INTO guardrail_events 
            (run_id, stage, unit_id, input_length, output_length, ratio, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.run_id,
            event.stage,
            event.unit_id,
            event.input_length,
            event.output_length,
            event.ratio,
            event.status,
            event.created_at.isoformat(),
        ))
        conn.commit()


# --------------------------------------------------
# Core guardrail function
# --------------------------------------------------

def record_condensation(
    input_text: str,
    output_text: str,
    stage: str,
    unit_id: str,
    use_tokens: bool = True,
) -> GuardrailEvent:
    """
    Record a condensation event and persist it to the database.
    
    This is the main entry point for guardrail instrumentation.
    Call this AFTER each condensation operation completes.
    
    Args:
        input_text: The text that was sent to the LLM for condensation
        output_text: The condensed text returned by the LLM
        stage: The pipeline stage ("chapter", "arc", "super-arc", etc.)
        unit_id: Identifier for the unit (e.g., "chapter_001", "arc_01")
        use_tokens: If True, measure in tokens; if False, use characters
    
    Returns:
        The GuardrailEvent that was recorded (for logging/inspection)
    
    IMPORTANT: This function NEVER raises exceptions that would halt the pipeline.
    Any errors are logged but swallowed to ensure guardrails remain non-blocking.
    """
    try:
        # Measure lengths
        if use_tokens:
            from utils import estimate_tokens
            input_length = estimate_tokens(input_text)
            output_length = estimate_tokens(output_text)
        else:
            input_length = len(input_text)
            output_length = len(output_text)
        
        # Calculate ratio (guard against division by zero)
        if input_length == 0:
            ratio = 0.0
        else:
            ratio = output_length / input_length
        
        # Classify the ratio
        status = classify_ratio(ratio, stage)
        
        # Create event
        event = GuardrailEvent(
            run_id=get_run_id(),
            stage=stage,
            unit_id=unit_id,
            input_length=input_length,
            output_length=output_length,
            ratio=ratio,
            status=status,
            created_at=datetime.utcnow(),
        )
        
        # Persist to database
        persist_event(event)
        
        # Log if not green (for immediate visibility during runs)
        if status != "green":
            status_symbol = "🟡" if status == "yellow" else "🔴"
            print(f"  {status_symbol} [{stage}] {unit_id}: ratio={ratio:.3f} ({status.upper()})")
        
        return event
        
    except Exception as e:
        # Guardrails must NEVER halt the pipeline
        # Log the error but continue execution
        print(f"  ⚠️ Guardrail error (non-blocking): {e}")
        # Return a dummy event to maintain interface contract
        return GuardrailEvent(
            run_id=get_run_id(),
            stage=stage,
            unit_id=unit_id,
            input_length=0,
            output_length=0,
            ratio=0.0,
            status="red",
            created_at=datetime.utcnow(),
        )


# --------------------------------------------------
# Run summary
# --------------------------------------------------

def get_run_summary(run_id: Optional[str] = None) -> dict:
    """
    Get a summary of guardrail events for a run.
    
    Args:
        run_id: The run to summarize. If None, uses current run.
    
    Returns:
        Dictionary with counts by status and total.
    """
    if run_id is None:
        run_id = get_run_id()
    
    with _db_context() as conn:
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM guardrail_events
            WHERE run_id = ?
            GROUP BY status
        """, (run_id,))
        
        counts = {"green": 0, "yellow": 0, "red": 0}
        for row in cursor.fetchall():
            counts[row[0]] = row[1]
        
        total = sum(counts.values())
        
        return {
            "run_id": run_id,
            "total": total,
            "green": counts["green"],
            "yellow": counts["yellow"],
            "red": counts["red"],
        }


def print_run_summary(run_id: Optional[str] = None) -> None:
    """
    Print a human-readable summary of guardrail events for a run.
    
    This should be called at the end of pipeline execution to give
    operators visibility into condensation health.
    """
    summary = get_run_summary(run_id)
    
    print("\n" + "=" * 50)
    print("GUARDRAIL SUMMARY")
    print("=" * 50)
    print(f"Run ID: {summary['run_id']}")
    print(f"Total condensation events: {summary['total']}")
    print(f"  🟢 GREEN:  {summary['green']}")
    print(f"  🟡 YELLOW: {summary['yellow']}")
    print(f"  🔴 RED:    {summary['red']}")
    
    if summary['red'] > 0:
        print("\n⚠️  WARNING: RED events detected - review recommended")
        print(f"   Query: SELECT * FROM guardrail_events WHERE run_id = '{summary['run_id']}' AND status = 'red'")
    elif summary['yellow'] > 0:
        print("\n📋 NOTE: YELLOW events present - consider reviewing")
    else:
        print("\n✅ All condensation events within expected parameters")
    
    print("=" * 50)
