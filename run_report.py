# run_report.py
"""
Unified Run Report for Abridge Pipeline

PURPOSE:
This module generates a post-run AUDIT ARTIFACT that aggregates all
observational data from a pipeline execution into a single, coherent summary.

WHY THIS EXISTS:
Information about a pipeline run is fragmented across:
- Console logs (transient)
- SQLite guardrail tables
- SQLite LLM usage tables
- Output directories

Without a unified report, answering basic audit questions requires manual
assembly from multiple sources. This module provides a single artifact
that answers:
- What ran and what was skipped?
- How safe was the run (guardrail signals)?
- How much did it cost?
- What artifacts were produced?

IMPORTANT DESIGN PRINCIPLES:
- Reports are AUDIT ARTIFACTS, not quality scores or pass/fail judgments
- Reports aggregate EXISTING data (never recompute or re-run anything)
- Report generation is NON-BLOCKING (failures are logged, never halt pipeline)
- Reports are APPEND-ONLY (never overwrite previous run reports)
- This is post-run aggregation, not execution-time instrumentation

NON-GOALS:
- Quality evaluation of the condensed output
- Semantic analysis of narrative content
- Dashboard or UI generation
- Real-time monitoring
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

from guardrails import GUARDRAIL_DB_PATH


# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Directory where run reports are stored
# Each report is named by run_id to prevent overwrites
REPORTS_DIR = os.getenv("ABRIDGE_REPORTS_DIR", "data/reports")

# Output directories (must match run_pipeline.py)
CHAPTERS_CONDENSED_DIR = "data/chapters_condensed"
ARCS_CONDENSED_DIR = "data/arcs_condensed"
NOVEL_CONDENSED_DIR = "data/novel_condensed"


# --------------------------------------------------
# Data structures
# --------------------------------------------------

@dataclass
class StageExecution:
    """
    Execution summary for a single pipeline stage.
    """
    stage_name: str
    executed: bool  # False if skipped
    unit_count: int  # Number of units processed (0 if skipped)
    skipped_reason: Optional[str] = None  # e.g., "--skip-chapters"


@dataclass
class GuardrailSummary:
    """
    Aggregated guardrail signals for a run.
    """
    total_events: int
    green_count: int
    yellow_count: int
    red_count: int
    red_unit_ids: list[str] = field(default_factory=list)
    # Per-stage breakdown (values are dicts with status counts)
    by_stage: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class CostSummary:
    """
    Aggregated LLM usage and cost for a run.
    """
    total_llm_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: Optional[float]
    models_used: list[str] = field(default_factory=list)
    # Per-stage breakdown
    by_stage: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class OutputArtifacts:
    """
    Paths to output artifacts produced by the run.
    """
    novel_condensed_path: Optional[str]
    chapters_condensed_dir: Optional[str]
    arcs_condensed_dir: Optional[str]
    intermediate_dirs: list[str] = field(default_factory=list)


@dataclass
class RunReport:
    """
    Complete unified report for a single pipeline run.
    
    This is the top-level structure that aggregates all run information
    into a single audit artifact.
    """
    # Run identity
    run_id: str
    novel_name: str
    start_time: Optional[str]
    end_time: Optional[str]
    report_generated_at: str
    
    # Configuration snapshot
    llm_provider: Optional[str]
    model_name: Optional[str]
    
    # Stage execution
    stages: list[StageExecution] = field(default_factory=list)
    
    # Guardrail summary
    guardrails: Optional[GuardrailSummary] = None
    
    # Cost summary
    cost: Optional[CostSummary] = None
    
    # Output artifacts
    artifacts: Optional[OutputArtifacts] = None
    
    # Any errors or warnings during report generation
    report_warnings: list[str] = field(default_factory=list)


# --------------------------------------------------
# Run metadata collection
# --------------------------------------------------

@dataclass
class RunMetadata:
    """
    Lightweight metadata collected DURING pipeline execution.
    
    This is populated as the pipeline runs, then used to generate the report.
    Kept minimal to avoid impacting execution performance.
    """
    run_id: str
    novel_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Stage tracking
    chapters_skipped: bool = False
    chapters_count: int = 0
    arcs_skipped: bool = False
    arcs_count: int = 0
    novel_skipped: bool = False
    
    # Model info (captured from first LLM call if possible)
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None


# Global metadata collector - populated during run_pipeline execution
_run_metadata: Optional[RunMetadata] = None


def init_run_metadata(run_id: str, novel_name: str) -> RunMetadata:
    """
    Initialize run metadata at the start of pipeline execution.
    
    Call this at the beginning of run_pipeline() to start collecting metadata.
    """
    global _run_metadata
    _run_metadata = RunMetadata(
        run_id=run_id,
        novel_name=novel_name,
        start_time=datetime.utcnow(),
    )
    return _run_metadata


def get_run_metadata() -> Optional[RunMetadata]:
    """Get the current run metadata, if initialized."""
    return _run_metadata


def finalize_run_metadata() -> Optional[RunMetadata]:
    """
    Finalize run metadata at the end of pipeline execution.
    
    Sets the end_time and returns the metadata for report generation.
    """
    global _run_metadata
    if _run_metadata is not None:
        _run_metadata.end_time = datetime.utcnow()
    return _run_metadata


def clear_run_metadata() -> None:
    """Clear run metadata after report generation."""
    global _run_metadata
    _run_metadata = None


# --------------------------------------------------
# SQLite data extraction
# --------------------------------------------------

def _get_db_connection() -> sqlite3.Connection:
    """Get a read-only connection to the SQLite database."""
    return sqlite3.connect(GUARDRAIL_DB_PATH)


def _query_guardrail_summary(run_id: str) -> GuardrailSummary:
    """
    Query guardrail data from SQLite for the given run.
    
    Aggregates counts by status and extracts RED unit_ids.
    """
    summary = GuardrailSummary(
        total_events=0,
        green_count=0,
        yellow_count=0,
        red_count=0,
        red_unit_ids=[],
        by_stage={},
    )
    
    try:
        conn = _get_db_connection()
        
        # Overall counts by status
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM guardrail_events
            WHERE run_id = ?
            GROUP BY status
        """, (run_id,))
        
        for row in cursor.fetchall():
            status, count = row
            if status == "green":
                summary.green_count = count
            elif status == "yellow":
                summary.yellow_count = count
            elif status == "red":
                summary.red_count = count
        
        summary.total_events = summary.green_count + summary.yellow_count + summary.red_count
        
        # RED unit_ids only (as specified in requirements)
        cursor = conn.execute("""
            SELECT unit_id FROM guardrail_events
            WHERE run_id = ? AND status = 'red'
            ORDER BY unit_id
        """, (run_id,))
        summary.red_unit_ids = [row[0] for row in cursor.fetchall()]
        
        # Per-stage breakdown
        cursor = conn.execute("""
            SELECT stage, status, COUNT(*) as count
            FROM guardrail_events
            WHERE run_id = ?
            GROUP BY stage, status
            ORDER BY stage
        """, (run_id,))
        
        for row in cursor.fetchall():
            stage, status, count = row
            if stage not in summary.by_stage:
                summary.by_stage[stage] = {"green": 0, "yellow": 0, "red": 0}
            summary.by_stage[stage][status] = count
        
        conn.close()
        
    except Exception as e:
        # Non-blocking: return partial data with warning
        summary.by_stage["_error"] = {"message": str(e)}
    
    return summary


def _query_cost_summary(run_id: str) -> CostSummary:
    """
    Query LLM usage data from SQLite for the given run.
    
    Aggregates token counts, cost, and models used.
    """
    summary = CostSummary(
        total_llm_calls=0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_tokens=0,
        estimated_cost_usd=None,
        models_used=[],
        by_stage={},
    )
    
    try:
        conn = _get_db_connection()
        
        # Overall aggregates
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as call_count,
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(output_tokens), 0) as total_output,
                SUM(estimated_cost) as total_cost
            FROM llm_usage_events
            WHERE run_id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        if row:
            summary.total_llm_calls = row[0] or 0
            summary.total_input_tokens = row[1] or 0
            summary.total_output_tokens = row[2] or 0
            summary.total_tokens = summary.total_input_tokens + summary.total_output_tokens
            summary.estimated_cost_usd = row[3]  # May be None
        
        # Distinct models used
        cursor = conn.execute("""
            SELECT DISTINCT model FROM llm_usage_events
            WHERE run_id = ?
            ORDER BY model
        """, (run_id,))
        summary.models_used = [row[0] for row in cursor.fetchall()]
        
        # Per-stage breakdown
        cursor = conn.execute("""
            SELECT 
                stage,
                COUNT(*) as calls,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                SUM(estimated_cost) as cost
            FROM llm_usage_events
            WHERE run_id = ?
            GROUP BY stage
            ORDER BY stage
        """, (run_id,))
        
        for row in cursor.fetchall():
            stage, calls, input_tok, output_tok, cost = row
            summary.by_stage[stage] = {
                "calls": calls,
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "cost": cost,
            }
        
        conn.close()
        
    except Exception as e:
        # Non-blocking: return partial data
        summary.by_stage["_error"] = {"message": str(e)}
    
    return summary


def _query_run_timestamps(run_id: str) -> tuple[Optional[str], Optional[str]]:
    """
    Query the first and last event timestamps for the run.
    
    Used to determine run duration when metadata is unavailable.
    """
    try:
        conn = _get_db_connection()
        
        # Get earliest timestamp from either table
        cursor = conn.execute("""
            SELECT MIN(created_at), MAX(created_at)
            FROM (
                SELECT created_at FROM guardrail_events WHERE run_id = ?
                UNION ALL
                SELECT created_at FROM llm_usage_events WHERE run_id = ?
            )
        """, (run_id, run_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0], row[1]
        return None, None
        
    except Exception:
        return None, None


# --------------------------------------------------
# Artifact discovery
# --------------------------------------------------

def _discover_artifacts(novel_name: str) -> OutputArtifacts:
    """
    Discover output artifacts for the given novel.
    
    Checks for existence of expected output paths.
    """
    artifacts = OutputArtifacts(
        novel_condensed_path=None,
        chapters_condensed_dir=None,
        arcs_condensed_dir=None,
        intermediate_dirs=[],
    )
    
    # Final novel condensation
    novel_path = os.path.join(NOVEL_CONDENSED_DIR, novel_name, "novel.condensed.txt")
    if os.path.isfile(novel_path):
        artifacts.novel_condensed_path = novel_path
    
    # Chapters directory
    chapters_dir = os.path.join(CHAPTERS_CONDENSED_DIR, novel_name)
    if os.path.isdir(chapters_dir):
        artifacts.chapters_condensed_dir = chapters_dir
    
    # Arcs directory
    arcs_dir = os.path.join(ARCS_CONDENSED_DIR, novel_name)
    if os.path.isdir(arcs_dir):
        artifacts.arcs_condensed_dir = arcs_dir
    
    # Intermediate reduction directories (created by reduce_until_fit)
    # These are subdirectories within novel_condensed_dir
    novel_dir = os.path.join(NOVEL_CONDENSED_DIR, novel_name)
    if os.path.isdir(novel_dir):
        for entry in os.listdir(novel_dir):
            subdir = os.path.join(novel_dir, entry)
            if os.path.isdir(subdir):
                artifacts.intermediate_dirs.append(subdir)
    
    return artifacts


# --------------------------------------------------
# Report generation
# --------------------------------------------------

def generate_run_report(
    run_id: str,
    novel_name: str,
    metadata: Optional[RunMetadata] = None,
) -> RunReport:
    """
    Generate a unified run report by aggregating all available data.
    
    Args:
        run_id: The unique identifier for this pipeline run
        novel_name: The name of the novel that was processed
        metadata: Optional runtime metadata (if collected during execution)
    
    Returns:
        A complete RunReport aggregating all run information.
    
    This function NEVER raises exceptions - it returns partial reports
    with warnings if some data is unavailable.
    """
    warnings = []
    
    # Determine timestamps
    if metadata:
        start_time = metadata.start_time.isoformat() if metadata.start_time else None
        end_time = metadata.end_time.isoformat() if metadata.end_time else None
    else:
        # Fall back to querying timestamps from database
        start_time, end_time = _query_run_timestamps(run_id)
        if not start_time:
            warnings.append("Could not determine run start time from database")
    
    # Build stage execution summary
    stages = []
    if metadata:
        stages.append(StageExecution(
            stage_name="chapter",
            executed=not metadata.chapters_skipped,
            unit_count=metadata.chapters_count,
            skipped_reason="--skip-chapters" if metadata.chapters_skipped else None,
        ))
        stages.append(StageExecution(
            stage_name="arc",
            executed=not metadata.arcs_skipped,
            unit_count=metadata.arcs_count,
            skipped_reason="--skip-arcs" if metadata.arcs_skipped else None,
        ))
        stages.append(StageExecution(
            stage_name="novel",
            executed=not metadata.novel_skipped,
            unit_count=1 if not metadata.novel_skipped else 0,
            skipped_reason="--skip-novel" if metadata.novel_skipped else None,
        ))
    else:
        warnings.append("No runtime metadata available - stage execution details unavailable")
    
    # Query guardrail summary from SQLite
    try:
        guardrails = _query_guardrail_summary(run_id)
    except Exception as e:
        warnings.append(f"Failed to query guardrail data: {e}")
        guardrails = None
    
    # Query cost summary from SQLite
    try:
        cost = _query_cost_summary(run_id)
    except Exception as e:
        warnings.append(f"Failed to query cost data: {e}")
        cost = None
    
    # Discover output artifacts
    try:
        artifacts = _discover_artifacts(novel_name)
    except Exception as e:
        warnings.append(f"Failed to discover artifacts: {e}")
        artifacts = None
    
    # Determine model info
    llm_provider = None
    model_name = None
    if metadata:
        llm_provider = metadata.llm_provider
        model_name = metadata.model_name
    elif cost and cost.models_used:
        # Infer from cost data
        model_name = cost.models_used[0] if len(cost.models_used) == 1 else ", ".join(cost.models_used)
    
    # Assemble the report
    report = RunReport(
        run_id=run_id,
        novel_name=novel_name,
        start_time=start_time,
        end_time=end_time,
        report_generated_at=datetime.utcnow().isoformat(),
        llm_provider=llm_provider,
        model_name=model_name,
        stages=stages,
        guardrails=guardrails,
        cost=cost,
        artifacts=artifacts,
        report_warnings=warnings,
    )
    
    return report


# --------------------------------------------------
# Report serialization
# --------------------------------------------------

def _dataclass_to_dict(obj: Any) -> Any:
    """
    Recursively convert dataclasses to dictionaries for JSON serialization.
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    else:
        return obj


def report_to_json(report: RunReport) -> str:
    """
    Serialize a RunReport to JSON string.
    """
    return json.dumps(_dataclass_to_dict(report), indent=2)


def report_to_markdown(report: RunReport) -> str:
    """
    Generate a human-readable Markdown summary from a RunReport.
    
    This is a DERIVED view of the same data as the JSON report.
    """
    lines = []
    
    # Header
    lines.append(f"# Abridge Run Report")
    lines.append("")
    lines.append(f"**Run ID:** `{report.run_id}`")
    lines.append(f"**Novel:** {report.novel_name}")
    lines.append(f"**Report Generated:** {report.report_generated_at}")
    lines.append("")
    
    # Run Identity
    lines.append("## Run Identity")
    lines.append("")
    lines.append(f"- **Start Time:** {report.start_time or 'N/A'}")
    lines.append(f"- **End Time:** {report.end_time or 'N/A'}")
    if report.llm_provider:
        lines.append(f"- **LLM Provider:** {report.llm_provider}")
    if report.model_name:
        lines.append(f"- **Model:** {report.model_name}")
    lines.append("")
    
    # Stage Execution
    if report.stages:
        lines.append("## Stage Execution")
        lines.append("")
        lines.append("| Stage | Executed | Units | Notes |")
        lines.append("|-------|----------|-------|-------|")
        for stage in report.stages:
            executed = "✅ Yes" if stage.executed else "⏭️ Skipped"
            notes = stage.skipped_reason or ""
            lines.append(f"| {stage.stage_name} | {executed} | {stage.unit_count} | {notes} |")
        lines.append("")
    
    # Guardrail Summary
    if report.guardrails:
        g = report.guardrails
        lines.append("## Guardrail Summary")
        lines.append("")
        lines.append(f"**Total Events:** {g.total_events}")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| 🟢 GREEN | {g.green_count} |")
        lines.append(f"| 🟡 YELLOW | {g.yellow_count} |")
        lines.append(f"| 🔴 RED | {g.red_count} |")
        lines.append("")
        
        if g.red_unit_ids:
            lines.append("### RED Unit IDs (Require Review)")
            lines.append("")
            for unit_id in g.red_unit_ids:
                lines.append(f"- `{unit_id}`")
            lines.append("")
        
        if g.by_stage and "_error" not in g.by_stage:
            lines.append("### By Stage")
            lines.append("")
            lines.append("| Stage | Green | Yellow | Red |")
            lines.append("|-------|-------|--------|-----|")
            for stage, counts in g.by_stage.items():
                lines.append(f"| {stage} | {counts.get('green', 0)} | {counts.get('yellow', 0)} | {counts.get('red', 0)} |")
            lines.append("")
    
    # Cost Summary
    if report.cost:
        c = report.cost
        lines.append("## Cost & Token Summary")
        lines.append("")
        lines.append(f"- **Total LLM Calls:** {c.total_llm_calls}")
        lines.append(f"- **Total Input Tokens:** {c.total_input_tokens:,}")
        lines.append(f"- **Total Output Tokens:** {c.total_output_tokens:,}")
        lines.append(f"- **Total Tokens:** {c.total_tokens:,}")
        if c.estimated_cost_usd is not None:
            lines.append(f"- **Estimated Cost:** ${c.estimated_cost_usd:.4f} USD")
        else:
            lines.append(f"- **Estimated Cost:** N/A (pricing not available)")
        lines.append("")
        
        if c.models_used:
            lines.append(f"**Models Used:** {', '.join(c.models_used)}")
            lines.append("")
        
        if c.by_stage and "_error" not in c.by_stage:
            lines.append("### By Stage")
            lines.append("")
            lines.append("| Stage | Calls | Input Tokens | Output Tokens | Cost |")
            lines.append("|-------|-------|--------------|---------------|------|")
            for stage, data in c.by_stage.items():
                cost_str = f"${data.get('cost', 0):.4f}" if data.get('cost') is not None else "N/A"
                lines.append(f"| {stage} | {data.get('calls', 0)} | {data.get('input_tokens', 0):,} | {data.get('output_tokens', 0):,} | {cost_str} |")
            lines.append("")
    
    # Output Artifacts
    if report.artifacts:
        a = report.artifacts
        lines.append("## Output Artifacts")
        lines.append("")
        if a.novel_condensed_path:
            lines.append(f"- **Final Novel:** `{a.novel_condensed_path}`")
        if a.chapters_condensed_dir:
            lines.append(f"- **Chapters Directory:** `{a.chapters_condensed_dir}`")
        if a.arcs_condensed_dir:
            lines.append(f"- **Arcs Directory:** `{a.arcs_condensed_dir}`")
        if a.intermediate_dirs:
            lines.append(f"- **Intermediate Directories:**")
            for d in a.intermediate_dirs:
                lines.append(f"  - `{d}`")
        lines.append("")
    
    # Warnings
    if report.report_warnings:
        lines.append("## Report Warnings")
        lines.append("")
        for warning in report.report_warnings:
            lines.append(f"- ⚠️ {warning}")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(f"*Report generated by Abridge Pipeline*")
    
    return "\n".join(lines)


# --------------------------------------------------
# Report persistence
# --------------------------------------------------

def save_run_report(report: RunReport) -> tuple[Optional[str], Optional[str]]:
    """
    Save a run report to disk as both JSON and Markdown.
    
    Reports are saved to REPORTS_DIR with filenames based on run_id.
    Never overwrites existing reports.
    
    Returns:
        Tuple of (json_path, markdown_path), with None for any failures.
    
    This function NEVER raises exceptions - it logs errors and returns None.
    """
    json_path = None
    md_path = None
    
    try:
        # Ensure reports directory exists
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Generate filenames based on run_id
        base_name = report.run_id
        json_file = os.path.join(REPORTS_DIR, f"{base_name}.json")
        md_file = os.path.join(REPORTS_DIR, f"{base_name}.md")
        
        # Save JSON report
        try:
            json_content = report_to_json(report)
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_content)
            json_path = json_file
        except Exception as e:
            print(f"  ⚠️ Failed to save JSON report: {e}")
        
        # Save Markdown report
        try:
            md_content = report_to_markdown(report)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            md_path = md_file
        except Exception as e:
            print(f"  ⚠️ Failed to save Markdown report: {e}")
        
    except Exception as e:
        print(f"  ⚠️ Failed to create reports directory: {e}")
    
    return json_path, md_path


# --------------------------------------------------
# Main entry point (for integration with run_pipeline.py)
# --------------------------------------------------

def generate_and_save_report(
    run_id: str,
    novel_name: str,
    metadata: Optional[RunMetadata] = None,
) -> None:
    """
    Generate and save the unified run report.
    
    This is the main entry point called at the end of pipeline execution.
    It is NON-BLOCKING - any errors are logged but do not halt execution.
    
    Args:
        run_id: The unique identifier for this pipeline run
        novel_name: The name of the novel that was processed
        metadata: Optional runtime metadata (if collected during execution)
    """
    try:
        print("\n" + "-" * 50)
        print("GENERATING RUN REPORT")
        print("-" * 50)
        
        # Generate the report
        report = generate_run_report(run_id, novel_name, metadata)
        
        # Save to disk
        json_path, md_path = save_run_report(report)
        
        if json_path:
            print(f"JSON report: {json_path}")
        if md_path:
            print(f"Markdown report: {md_path}")
        
        if report.report_warnings:
            print(f"Report generated with {len(report.report_warnings)} warning(s)")
        
        print("-" * 50)
        
    except Exception as e:
        # Report generation must NEVER halt the pipeline
        print(f"  ⚠️ Report generation failed (non-blocking): {e}")
