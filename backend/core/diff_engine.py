"""
NEXUS — Layer 8: Diff Engine
Applies proposed changes, computes real unified diffs, calculates minimality score.
Rejects any change where old_code does not exist verbatim in the file.
"""
import difflib
from typing import Dict, List, Any

import structlog
logger = structlog.get_logger()


def apply_changes(original_content: str, proposed_changes: List[Dict]) -> Dict:
    """
    Apply a list of proposed changes to the original file.
    Each change: {issue_type, old_code, new_code, line_start, line_end, reason}

    Returns:
    {
        original_file, modified_file, unified_diff,
        changes_applied, changes_rejected, minimality_score,
        lines_changed, total_lines, rejection_reasons
    }
    """
    modified = original_content
    applied = []
    rejected = []
    rejection_reasons = []

    # Sort by line number descending so later replacements don't shift earlier line numbers
    sorted_changes = sorted(proposed_changes, key=lambda c: c.get("line_start", 0), reverse=True)

    for change in sorted_changes:
        old_code = change.get("old_code", "")
        new_code = change.get("new_code", "")

        if not old_code:
            rejected.append(change)
            rejection_reasons.append({
                "issue_type": change.get("issue_type"),
                "reason": "old_code is empty",
            })
            continue

        # CRITICAL GUARD: old_code must exist verbatim
        if old_code not in modified:
            rejected.append(change)
            rejection_reasons.append({
                "issue_type": change.get("issue_type"),
                "reason": f"old_code not found verbatim in file: {repr(old_code[:60])}",
            })
            logger.warning(
                "change_rejected_not_found",
                issue_type=change.get("issue_type"),
                old_code_preview=old_code[:60],
            )
            continue

        # Apply the replacement (first occurrence only — precise)
        modified = modified.replace(old_code, new_code, 1)
        applied.append(change)
        logger.info("change_applied", issue_type=change.get("issue_type"))

    # Compute unified diff
    original_lines = original_content.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="original",
        tofile="modernized",
        lineterm="",
    ))
    unified_diff = "".join(diff_lines)

    # Minimality score: % of file that was NOT changed
    total_lines = len(original_lines)
    changed_lines = sum(1 for line in diff_lines if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    minimality = round(((total_lines - changed_lines / 2) / total_lines * 100), 2) if total_lines else 100.0
    minimality = max(0.0, min(100.0, minimality))

    if minimality < 80:
        logger.warning("low_minimality_score", score=minimality)

    return {
        "original_file":    original_content,
        "modified_file":    modified,
        "unified_diff":     unified_diff,
        "changes_applied":  len(applied),
        "changes_rejected": len(rejected),
        "rejected_changes": rejected,
        "rejection_reasons": rejection_reasons,
        "minimality_score": minimality,
        "lines_changed":    changed_lines // 2,
        "total_lines":      total_lines,
    }


def compute_diff_only(original: str, modified: str) -> str:
    """Just compute the diff between two strings (used by chunk validator)."""
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile="original",
        tofile="modernized",
        lineterm="",
    ))