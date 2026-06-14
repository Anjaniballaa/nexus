"""
NEXUS — Main Pipeline Orchestrator
Runs all 14 layers in sequence. Broadcasts progress via WebSocket.
Called by the API routes.
"""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.config import settings
from core.database import Analysis, ProposedChange
from core.language_detector import detect_language
from core.treesitter_parser import parse_file, validate_ast_after_change
from core.security_scanner import scan_file
from core.diff_engine import apply_changes
from core.chunk_validator import validate_modified_file
from core.test_runner import detect_and_run_tests
from core.observability import LayerTrace, broadcast
from agents.reader import analyze as reader_analyze
from agents.modernizer import generate_fixes
from agents.risk_scorer import score_changes
from agents.documenter import generate_report
from evaluation.evaluation_engine import evaluate as evaluate_confidence

import structlog
logger = structlog.get_logger()


async def run_pipeline(
    analysis_id: str,
    files: List[Dict],          # [{"path": str, "content": str}]
    db: AsyncSession,
    repo_path: Optional[str] = None,
) -> Dict:
    """
    Run the full 14-layer NEXUS pipeline.
    Updates the Analysis record in DB as it progresses.
    Broadcasts layer events via WebSocket.
    """

    # Update status to running
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise ValueError(f"Analysis {analysis_id} not found")

    analysis.status = "running"
    await db.commit()

    try:
        final_report = await _run_all_layers(
            analysis_id, files, analysis, db, repo_path
        )
        analysis.status = "complete"
        analysis.completed_at = datetime.utcnow()
        await db.commit()
        return final_report

    except Exception as e:
        logger.error("pipeline_failed", analysis_id=analysis_id, error=str(e))
        analysis.status = "failed"
        analysis.error_message = str(e)
        await db.commit()
        raise


async def _run_all_layers(
    analysis_id: str,
    files: List[Dict],
    analysis: Analysis,
    db: AsyncSession,
    repo_path: Optional[str],
) -> Dict:
    """Execute each layer, accumulating results."""

    all_results = {
        "files": [],
        "language_breakdown": {},
        "total_issues": 0,
        "total_security": 0,
        "all_changes": [],
        "all_risks": [],
    }

    for file_info in files:
        file_path = file_info["path"]
        content = file_info["content"]

        await broadcast(analysis_id, {
            "type": "file_start",
            "file": file_path,
            "timestamp": datetime.utcnow().isoformat(),
        })

        file_result = await _process_single_file(
            analysis_id, file_path, content, db, repo_path
        )
        all_results["files"].append(file_result)

        # Accumulate language breakdown
        lang = file_result.get("language_info", {}).get("language", "Unknown")
        all_results["language_breakdown"][lang] = \
            all_results["language_breakdown"].get(lang, 0) + 1

        all_results["total_issues"] += len(file_result.get("issues", []))
        all_results["total_security"] += len(
            file_result.get("security_result", {}).get("security_findings", [])
        )
        all_results["all_changes"].extend(file_result.get("validated_changes", []))
        all_results["all_risks"].append(file_result.get("risk_result", {}))

    # Convert language breakdown to percentages
    total_files = len(files)
    if total_files > 0:
        all_results["language_breakdown"] = {
            lang: round(count / total_files * 100)
            for lang, count in all_results["language_breakdown"].items()
        }

    # Update analysis record with summary
    analysis.total_files = total_files
    analysis.total_issues = all_results["total_issues"]
    analysis.security_issues = all_results["total_security"]
    analysis.language_breakdown = all_results["language_breakdown"]

    if files:
        first = all_results["files"][0]
        analysis.language = first.get("language_info", {}).get("language")
        analysis.era = first.get("language_info", {}).get("era")
        analysis.minimality_score = first.get("diff_result", {}).get("minimality_score")
        analysis.complexity_before = (
            first.get("security_result", {})
            .get("complexity_before", {})
            .get("avg_cyclomatic")
        )
        analysis.tests_passed = not first.get("test_result", {}).get("regression_detected", False)
        analysis.test_count = (
            first.get("test_result", {})
            .get("modified_results", {})
            .get("passed", 0)
        )
        analysis.confidence_score = first.get("evaluation_result", {}).get("confidence_score")
        analysis.estimated_hours_saved = first.get("risk_result", {}).get("estimated_hours_saved")
        analysis.overall_risk = first.get("risk_result", {}).get("overall_risk")

    await db.commit()

    await broadcast(analysis_id, {
        "type": "pipeline_complete",
        "summary": {
            "total_files": total_files,
            "total_issues": all_results["total_issues"],
            "language_breakdown": all_results["language_breakdown"],
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    return all_results


async def _process_single_file(
    analysis_id: str,
    file_path: str,
    content: str,
    db: AsyncSession,
    repo_path: Optional[str],
) -> Dict:
    """Run all pipeline layers for one file."""

    # ── Layer 1: Language Detection ──────────────────────────────────────────
    async with LayerTrace(analysis_id, "language_detector", {"file": file_path}):
        language_info = detect_language(file_path, content)
        language = language_info["language"]

    # Skip unknown languages
    if language == "Unknown":
        return {"file_path": file_path, "skipped": True, "reason": "Unknown language"}

    # ── Layer 2: AST Parsing ─────────────────────────────────────────────────
    async with LayerTrace(analysis_id, "ast_parser", {"language": language}):
        ast_result = await asyncio.get_event_loop().run_in_executor(
            None, parse_file, language, content, file_path
        )

    # ── Layer 3: Security Scan ───────────────────────────────────────────────
    async with LayerTrace(analysis_id, "security_scanner"):
        security_result = await asyncio.get_event_loop().run_in_executor(
            None, scan_file, file_path, content, language
        )

    # ── Layer 4: Reader Agent ─────────────────────────────────────────────────
    async with LayerTrace(analysis_id, "reader_agent"):
        issues = await asyncio.get_event_loop().run_in_executor(
            None,
            reader_analyze,
            content, language_info, ast_result, security_result, file_path,
        )

    if not issues:
        return {
            "file_path": file_path,
            "language_info": language_info,
            "ast_result": ast_result,
            "security_result": security_result,
            "issues": [],
            "validated_changes": [],
            "message": "No legacy issues found",
        }

    # ── Layer 5: Modernizer Agent ─────────────────────────────────────────────
    async with LayerTrace(analysis_id, "modernizer_agent", {"issues": len(issues)}):
        raw_changes = await asyncio.get_event_loop().run_in_executor(
            None, generate_fixes, content, issues, language_info, ast_result
        )

    # ── Layer 6: Diff Engine ──────────────────────────────────────────────────
    async with LayerTrace(analysis_id, "diff_engine"):
        validated_only = [c for c in raw_changes if c.get("status") == "validated"]
        diff_result = apply_changes(content, validated_only)

    # ── Layer 7: Chunk Validator ──────────────────────────────────────────────
    async with LayerTrace(analysis_id, "chunk_validator"):
        validation_result = validate_modified_file(
            language,
            content,
            diff_result["modified_file"],
            ast_result,
        )

    if not validation_result["validation_passed"]:
        await broadcast(analysis_id, {
            "type": "validation_failed",
            "file": file_path,
            "issues": validation_result["issues"],
        })

    # ── Layer 8: Test Runner ──────────────────────────────────────────────────
    async with LayerTrace(analysis_id, "test_runner"):
        test_result = await asyncio.get_event_loop().run_in_executor(
            None,
            detect_and_run_tests,
            content,
            diff_result["modified_file"],
            file_path,
            language,
            repo_path,
        )

    # Block changes if regression detected
    if test_result.get("regression_detected"):
        await broadcast(analysis_id, {
            "type": "regression_blocked",
            "file": file_path,
            "message": "Regression detected — changes blocked until tests pass",
        })
        validated_only = []   # Clear changes on regression

    # ── Layer 9: Risk Scorer ──────────────────────────────────────────────────
    async with LayerTrace(analysis_id, "risk_scorer"):
        risk_result = await asyncio.get_event_loop().run_in_executor(
            None,
            score_changes,
            raw_changes, diff_result, test_result,
            ast_result, security_result, language_info,
        )

    # ── Layer 10: Evaluation Engine ───────────────────────────────────────────
    async with LayerTrace(analysis_id, "evaluation_engine"):
        evaluation_result = evaluate_confidence(language, raw_changes)

    # ── Layer 11: Documenter Agent ────────────────────────────────────────────
    async with LayerTrace(analysis_id, "documenter_agent"):
        report = await asyncio.get_event_loop().run_in_executor(
            None,
            generate_report,
            language_info, security_result, issues, raw_changes,
            diff_result, test_result, risk_result, validation_result,
            evaluation_result, file_path, analysis_id,
        )
    # ── Save report to analysis ───────────────────────────────────────────────
    result_obj = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis_obj = result_obj.scalar_one_or_none()
    if analysis_obj:
        analysis_obj.report_markdown = report.get("full_markdown", "")
        analysis_obj.full_report = {
            **(analysis_obj.full_report or {}),
            "report": report,
            "executive_summary": report.get("executive_summary", ""),
        }
        await db.commit()
    # ── Save proposed changes to DB ───────────────────────────────────────────
    per_change_risk = {
        r.get("issue_type"): r
        for r in risk_result.get("per_change_risk", [])
    }

    for change in raw_changes:
        if change.get("status") not in ("validated", "manual_required"):
            continue
        risk_info = per_change_risk.get(change.get("issue_type"), {})
        db.add(ProposedChange(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            file_path=file_path,
            issue_type=change.get("issue_type", "unknown"),
            description=change.get("reason", ""),
            old_code=change.get("old_code", ""),
            new_code=change.get("new_code", ""),
            line_start=change.get("line_start", 0),
            line_end=change.get("line_end", 0),
            risk_level=risk_info.get("risk", "MEDIUM"),
            risk_reason=risk_info.get("reason", ""),
            confidence=risk_info.get("confidence"),
            priority=change.get("priority", 2),
            callers=risk_info.get("callers_affected", 0),
            status=change.get("status", "pending"),
        ))

    await db.commit()

    return {
        "file_path": file_path,
        "language_info": language_info,
        "ast_result": ast_result,
        "security_result": security_result,
        "issues": issues,
        "raw_changes": raw_changes,
        "validated_changes": validated_only,
        "diff_result": diff_result,
        "validation_result": validation_result,
        "test_result": test_result,
        "risk_result": risk_result,
        "evaluation_result": evaluation_result,
        "report": report,
    }