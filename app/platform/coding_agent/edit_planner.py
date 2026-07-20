"""
Edit planner — asks the configured model to propose concrete edit operations.

Returns a structured EditContract, not raw model text.
The model is a reasoning engine, not the executor.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import EditContract, EditOperation
from app.platform.runtime.service import invoke_ai


EDIT_PLANNER_SYSTEM = """You are a precise code editor inside AI Software Factory.

Your task: produce a machine-validatable edit plan for concrete file changes.

STRATEGY PRIORITY (prefer minimal changes):
1. ast_replace — Replace ONLY the specific function/class/method that changed.
   Set strategy="ast_replace", provide the COMPLETE replacement source in content,
   set target_symbol="FunctionName" and target_type="function"|"class"|"method".
2. apply_patch — Provide a unified diff showing only the lines that changed.
   Set strategy="apply_patch", content=unified diff with context lines.
3. replace_file — Full file replacement (FALLBACK ONLY, avoid when possible).
   Set strategy="replace_file", content=COMPLETE new file content.

Rules:
- ALWAYS prefer ast_replace when changing a single function/class/method.
- ALWAYS prefer apply_patch for small line-level changes.
- Only use replace_file when rewriting most of the file or creating new files.
- Never use prose instructions like "modify this function" or "add logic here".
- Never use TODOs, pseudocode, or placeholder comments.
- Every edit must be standalone and compilable.
- Return ONLY valid JSON matching this exact structure:

{
  "edits": [
    {
      "path": "relative/path/to/file.py",
      "operation": "update",
      "strategy": "ast_replace",
      "content": "...replacement function/class source...",
      "target_symbol": "FunctionName",
      "target_type": "function",
      "reason": "Why this edit is needed",
      "source_evidence": ["path/to/evidence"],
      "expected_effect": "What should change",
      "risk": "low"
    }
  ],
  "validation_commands": [
    {"argv": ["python3", "-m", "compileall", "app"], "reason": "Compile check"}
  ],
  "assumptions": [],
  "risks": []
}

For replace_file strategy, content MUST contain the COMPLETE new file content.
For apply_patch strategy, content MUST be a valid unified diff with ---, +++, @@ headers.
For ast_replace strategy, content is the complete replacement source for the target symbol.
For creates, use strategy="replace_file" with the full content.
For deletes, use strategy="replace_file" with content="".

Output only the JSON object. No markdown fences, no explanation.
"""


def plan_edits(
    mission_id: str,
    iteration: int,
    objective: str,
    context: Dict[str, Any],
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> EditContract:
    """
    Ask the model to propose a structured edit plan.

    Args:
        mission_id: Canonical MISSION-* identifier.
        iteration: Current iteration number (1-indexed).
        objective: Implementation objective.
        context: Bounded context from ContextBuilder.
        model: Optional model override.
        provider: Optional provider override.

    Returns:
        EditContract with structured edit operations.
    """
    prompt = _build_edit_prompt(mission_id, iteration, objective, context)

    ai_result = invoke_ai({
        "system": EDIT_PLANNER_SYSTEM,
        "prompt": prompt,
        "model": model,
        "provider": provider,
    })

    return _parse_edit_contract(mission_id, iteration, objective, ai_result)


def _build_edit_prompt(
    mission_id: str,
    iteration: int,
    objective: str,
    context: Dict[str, Any],
) -> str:
    """Build the edit-planning prompt with bounded context."""
    evidence = context.get("evidence", {})
    files = evidence.get("files", [])

    # Build a compact context: paths + content
    file_context_parts: List[str] = []
    for item in files:
        path = item.get("path", "unknown")
        content = item.get("content", "")
        fingerprint = item.get("fingerprint", "")
        file_context_parts.append(
            "=== FILE: %s (fingerprint: %s) ===\n%s" % (path, fingerprint, content)
        )

    constraints = context.get("architecture_constraints", [])
    constraints_text = "\n".join("- %s" % c for c in constraints) if constraints else "None"

    return """Mission: %s
Iteration: %s
Objective: %s

Architecture Constraints:
%s

Repository Evidence:
%s

Produce a concrete edit plan. For each file change, provide the COMPLETE file content.
""" % (
        mission_id,
        iteration,
        objective,
        constraints_text,
        "\n\n".join(file_context_parts),
    )


def _parse_edit_contract(
    mission_id: str,
    iteration: int,
    objective: str,
    ai_result: Dict[str, Any],
) -> EditContract:
    """Parse model output into a validated EditContract."""
    output_text = str(ai_result.get("output_text") or "").strip()

    # Strip markdown fences if present
    if output_text.startswith("```"):
        lines = output_text.split("\n")
        # Remove first line (```json or ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        output_text = "\n".join(lines)

    try:
        data = json.loads(output_text)
    except json.JSONDecodeError:
        # Try to find JSON block
        start = output_text.find("{")
        end = output_text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(output_text[start:end + 1])
            except json.JSONDecodeError:
                return EditContract(
                    mission_id=mission_id,
                    iteration=iteration,
                    objective=objective,
                    assumptions=["Model output could not be parsed as valid JSON."],
                    risks=["Invalid model output"],
                )
        else:
            return EditContract(
                mission_id=mission_id,
                iteration=iteration,
                objective=objective,
                assumptions=["Model output could not be parsed as valid JSON."],
                risks=["Invalid model output"],
            )

    edits: List[EditOperation] = []
    for raw in data.get("edits", []):
        if not isinstance(raw, dict):
            continue
        edits.append(EditOperation(
            path=str(raw.get("path", "")).strip(),
            operation=str(raw.get("operation", "update")).strip(),
            strategy=str(raw.get("strategy", "replace_file")).strip(),
            content=str(raw.get("content", "")),
            reason=str(raw.get("reason", "")).strip(),
            source_evidence=list(raw.get("source_evidence", [])),
            expected_effect=str(raw.get("expected_effect", "")).strip(),
            risk=str(raw.get("risk", "low")).strip(),
            target_symbol=str(raw.get("target_symbol", "")).strip(),
            target_type=str(raw.get("target_type", "")).strip(),
        ))

    validation_commands: List[Dict[str, Any]] = []
    for cmd in data.get("validation_commands", []):
        if isinstance(cmd, dict):
            validation_commands.append({
                "argv": list(cmd.get("argv", [])),
                "reason": str(cmd.get("reason", "")),
            })

    return EditContract(
        mission_id=mission_id,
        iteration=iteration,
        objective=objective,
        edits=edits,
        validation_commands=validation_commands,
        assumptions=list(data.get("assumptions", [])),
        risks=list(data.get("risks", [])),
    )
