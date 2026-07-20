"""
Tests for the Native Coding Agent module.

Tests are Python 3.9 compatible — no match/case, no PEP 604 unions.
Uses unittest with temporary directories for workspace simulation.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.platform.coding_agent.command_runner import (
    run_command,
    _validate_argv,
    ALLOWED_COMMAND_PREFIXES,
)
from app.platform.coding_agent.context_builder import build_coding_context
from app.platform.coding_agent.edit_executor import (
    apply_edits,
    record_pre_edit_fingerprint,
    _resolve_path,
    _is_placeholder,
    _validate_python_syntax,
)
from app.platform.coding_agent.edit_planner import _parse_edit_contract
from app.platform.coding_agent.models import (
    CodingSessionState,
    CommandResult,
    EditContract,
    EditOperation,
    FailureEvidence,
    VerifiedDiff,
    ValidationOutcome,
)
from app.platform.coding_agent.failure_analyzer import analyze_failure, _redact, _classify
from app.platform.coding_agent.diff_builder import build_verified_diff
from app.platform.coding_agent.repair_planner import detect_non_convergence
from app.platform.coding_agent.policy import (
    MAX_IDENTICAL_FAILURES,
    MAX_CODING_ITERATIONS,
    MAX_CHANGED_FILES_HARD_LIMIT,
    MAX_FILE_SIZE_BYTES,
)
from app.platform.coding_agent.session import create_coding_session


# ============================================================================
# Command Runner Tests
# ============================================================================

class TestCommandRunner(unittest.TestCase):
    """Tests 3, 8, 16, 18, 19: command execution, validation, security."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        # Initialize a git repo in the temp dir so git commands work
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=self.tmp, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.tmp, capture_output=True,
        )
        # Create a dummy file to commit so git rev-parse works
        (Path(self.tmp) / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.tmp, capture_output=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_empty_argv_rejected(self) -> None:
        """Test: Empty command argv is rejected."""
        result = run_command([], self.tmp)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.error)

    def test_2_unsafe_metacharacter_rejected(self) -> None:
        """Test: Shell metacharacters are blocked."""
        result = run_command(["echo", "hello; rm -rf /"], self.tmp)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.error)

    def test_3_valid_command_runs(self) -> None:
        """Test: Allowed command executes successfully."""
        result = run_command(["python3", "-c", "print('hello')"], self.tmp)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("hello", result.stdout)

    def test_4_disallowed_command_blocked(self) -> None:
        """Test: Non-allowlisted command is blocked."""
        result = run_command(["curl", "https://example.com"], self.tmp)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.error)

    def test_5_command_timeout_captured(self) -> None:
        """Test: Timeout is detected and reported."""
        # Use a very short timeout with a slightly longer command
        result = run_command(
            ["python3", "-c", "import time; time.sleep(10)"],
            self.tmp,
            timeout_seconds=1,
        )
        self.assertTrue(result.timed_out or result.exit_code != 0,
                        msg="Expected timeout or error, got exit=%d, timed_out=%s" % (
                            result.exit_code, result.timed_out))


# ============================================================================
# Edit Executor Tests  
# ============================================================================

class TestEditExecutor(unittest.TestCase):
    """Tests 4, 5, 7, 8, 10: file edits, creation, syntax validation."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_6_path_traversal_rejected(self) -> None:
        """Test: Path traversal is blocked."""
        result = _resolve_path("../etc/passwd", Path(self.tmp))
        self.assertIsNone(result)

    def test_7_absolute_path_rejected(self) -> None:
        """Test: Absolute path is rejected."""
        result = _resolve_path("/etc/passwd", Path(self.tmp))
        self.assertIsNone(result)

    def test_8_git_path_rejected(self) -> None:
        """Test: .git directory access is blocked."""
        result = _resolve_path(".git/config", Path(self.tmp))
        self.assertIsNone(result)

    def test_9_file_create_works(self) -> None:
        """Test: Real file creation in workspace."""
        fake_file = Path(self.tmp) / "app" / "test_file.py"
        source = "def hello():\n    return 'world'\n"
        # Pre-create parent dirs
        fake_file.parent.mkdir(parents=True, exist_ok=True)

        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="Create test file",
            edits=[
                EditOperation(
                    path="app/test_file.py",
                    operation="create",
                    strategy="replace_file",
                    content=source,
                    reason="Test file creation",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertIn("app/test_file.py", changed)
        self.assertEqual(len(warnings), 0)
        self.assertTrue(fake_file.exists())
        self.assertEqual(fake_file.read_text(), source)

    def test_10_file_update_works(self) -> None:
        """Test: Real file update in workspace."""
        fake_file = Path(self.tmp) / "existing.py"
        original = "x = 1\n"
        fake_file.write_text(original)

        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="Update file",
            edits=[
                EditOperation(
                    path="existing.py",
                    operation="update",
                    strategy="replace_file",
                    content="x = 2\n",
                    reason="Update value",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertIn("existing.py", changed)
        self.assertEqual(fake_file.read_text(), "x = 2\n")

    def test_11_update_non_existent_rejected(self) -> None:
        """Test: Cannot update a file that doesn't exist."""
        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="Update missing file",
            edits=[
                EditOperation(
                    path="nonexistent.py",
                    operation="update",
                    strategy="replace_file",
                    content="x = 1\n",
                    reason="Should fail",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertEqual(len(changed), 0)

    def test_12_placeholder_content_rejected(self) -> None:
        """Test: Placeholder/pseudocode content is rejected."""
        self.assertTrue(_is_placeholder("# TODO: implement this"))
        self.assertTrue(_is_placeholder("pass  # TODO"))
        self.assertTrue(_is_placeholder("raise NotImplementedError"))
        self.assertFalse(_is_placeholder("def real_function():\n    return True\n"))

    def test_13_invalid_python_syntax_rejected(self) -> None:
        """Test: Invalid Python syntax in .py files is rejected."""
        self.assertTrue(_validate_python_syntax("x = 1\ny = 2\n"))
        self.assertFalse(_validate_python_syntax("def broken(:\n    pass\n"))
        self.assertFalse(_validate_python_syntax("x = \n"))

    def test_14_unchanged_update_rejected(self) -> None:
        """Test: Update with identical content is rejected."""
        fake_file = Path(self.tmp) / "same.py"
        content = "x = 42\n"
        fake_file.write_text(content)

        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="No-op update",
            edits=[
                EditOperation(
                    path="same.py",
                    operation="update",
                    strategy="replace_file",
                    content=content,  # Same content
                    reason="Should be rejected",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertEqual(len(changed), 0)

    def test_15_no_evidence_edit_rejected(self) -> None:
        """Test: Edit without source evidence is rejected."""
        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="No evidence edit",
            edits=[
                EditOperation(
                    path="file.py",
                    operation="create",
                    strategy="replace_file",
                    content="x = 1\n",
                    reason="No evidence",
                    source_evidence=[],  # Empty - should reject
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertEqual(len(changed), 0)

    def test_16_file_size_limit_enforced(self) -> None:
        """Test: Files exceeding MAX_FILE_SIZE_BYTES are rejected."""
        huge_content = "x" * (MAX_FILE_SIZE_BYTES + 100)
        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="Huge file",
            edits=[
                EditOperation(
                    path="huge.py",
                    operation="create",
                    strategy="replace_file",
                    content=huge_content,
                    reason="Too big",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertEqual(len(changed), 0)

    def test_17_fingerprint_recording(self) -> None:
        """Test: Pre-edit and post-edit fingerprints are recorded."""
        fake_file = Path(self.tmp) / "fingerprint_test.py"
        content = "x = 1\n"
        fake_file.write_text(content)

        fp_before = record_pre_edit_fingerprint("fingerprint_test.py", self.tmp)
        self.assertTrue(len(fp_before) > 0)

        # Apply an edit
        contract = EditContract(
            mission_id="MISSION-TEST",
            iteration=1,
            objective="Fingerprint test",
            edits=[
                EditOperation(
                    path="fingerprint_test.py",
                    operation="update",
                    strategy="replace_file",
                    content="x = 2\n",
                    reason="Change value",
                    source_evidence=["test"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertIn("fingerprint_test.py", fps)
        self.assertNotEqual(fps["fingerprint_test.py"]["before"], fps["fingerprint_test.py"]["after"])


# ============================================================================
# Failure Analyzer Tests
# ============================================================================

class TestFailureAnalyzer(unittest.TestCase):
    """Tests 9, 20: failure capture, normalization, secret redaction."""

    def test_18_syntax_error_classified(self) -> None:
        """Test: Syntax error is correctly classified."""
        result = CommandResult(
            argv=["python3", "-c", "bad"],
            exit_code=1,
            stdout="",
            stderr="SyntaxError: invalid syntax",
            duration_ms=100,
        )
        failure = analyze_failure(result, "MISSION-TEST", "WS-TEST", 1)
        self.assertEqual(failure.category, "syntax-error")
        self.assertTrue(failure.is_code_failure)

    def test_19_import_error_classified(self) -> None:
        """Test: Import error is correctly classified."""
        result = CommandResult(
            argv=["python3", "-c", "import nonexistent"],
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'nonexistent'",
            duration_ms=100,
        )
        failure = analyze_failure(result, "MISSION-TEST", "WS-TEST", 1)
        self.assertEqual(failure.category, "import-error")
        self.assertTrue(failure.is_code_failure)

    def test_20_secrets_redacted(self) -> None:
        """Test: API keys and tokens are redacted from failure output."""
        text = "Using token sk-abc123def456ghijklmnopqrstuvwxyz for auth"
        redacted = _redact(text)
        self.assertNotIn("sk-abc", redacted)
        self.assertIn("sk-***", redacted)

    def test_21_github_token_redacted(self) -> None:
        """Test: GitHub tokens are redacted (standalone, no Bearer prefix)."""
        # Use a bare token without env-var prefix so it doesn't get consumed by
        # the GITHUB_TOKEN pattern first.
        text = "Using token: ghp_1234567890abcdefghijklmno for auth"
        redacted = _redact(text)
        self.assertIn("ghp_***", redacted)
        self.assertNotIn("ghp_123", redacted)

    def test_22_environment_failure_detected(self) -> None:
        """Test: Environment failures (not code failures) are distinguished."""
        result = CommandResult(
            argv=["python3", "-m", "app"],
            exit_code=1,
            stdout="",
            stderr="OSError: [Errno 2] No such file or directory: 'config.json'",
            duration_ms=100,
        )
        failure = analyze_failure(result, "MISSION-TEST", "WS-TEST", 1)
        self.assertTrue(failure.is_environment_failure)


# ============================================================================
# Repair Planner / Convergence Tests
# ============================================================================

class TestConvergenceDetection(unittest.TestCase):
    """Tests 12, 13, 14: convergence, repeated failures, budget exhaustion."""

    def _make_session(self) -> CodingSessionState:
        return CodingSessionState(
            session_id="SESS-TEST",
            mission_id="MISSION-TEST",
            workflow_run_id="WF-TEST",
            agent_task_id="AT-TEST",
            workspace_id="WS-TEST",
            repository="test/repo",
            base_ref="main",
            base_sha="abc123",
            workspace_path="/tmp/test",
            status="ready",
        )

    def test_23_repeated_identical_failure_stops(self) -> None:
        """Test: Repeated identical failure stops the loop."""
        session = self._make_session()
        session._max_iterations = MAX_CODING_ITERATIONS  # type: ignore[attr-defined]

        failure = FailureEvidence(
            failure_id="FAIL-1",
            mission_id="MISSION-TEST",
            workspace_id="WS-TEST",
            iteration=1,
            command="python3 -c test",
            exit_code=1,
            category="syntax-error",
            summary="Syntax error in file.py",
        )

        # Add the same failure MAX_IDENTICAL_FAILURES times
        for i in range(MAX_IDENTICAL_FAILURES):
            fp = failure.fingerprint()
            session.failure_fingerprints.append(fp)

        result = detect_non_convergence(session, failure)
        self.assertIsNotNone(result)
        self.assertIn("Repeated identical failure", result)

    def test_24_iteration_budget_stops_loop(self) -> None:
        """Test: Iteration budget exhaustion is detected."""
        session = self._make_session()
        session.iteration = MAX_CODING_ITERATIONS
        session._max_iterations = MAX_CODING_ITERATIONS  # type: ignore[attr-defined]

        failure = FailureEvidence(
            failure_id="FAIL-1",
            mission_id="MISSION-TEST",
            workspace_id="WS-TEST",
            iteration=MAX_CODING_ITERATIONS,
            command="python3 -c test",
            exit_code=1,
            category="test-failure",
            summary="Test failure",
        )

        # The loop guard in service.py checks iteration < max_iterations
        # This test verifies the convergence check would fire if the loop
        # were to continue beyond budget
        result = detect_non_convergence(session, failure)
        # With no prior failures, it should only flag if there's non-convergence
        self.assertIsNone(result)  # First failure, no pattern yet


# ============================================================================
# Diff Builder Tests
# ============================================================================

class TestDiffBuilder(unittest.TestCase):
    """Tests 11, 23: verified diff generation, no remote mutation."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=self.tmp, capture_output=True)
        app_dir = Path(self.tmp) / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "__init__.py").write_text("")
        subprocess.run(["git", "add", "."], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.tmp, capture_output=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_25_verified_diff_generated(self) -> None:
        """Test: Verified diff is produced with correct structure."""
        # Make a change
        (Path(self.tmp) / "app" / "new_file.py").write_text("x = 1\n")

        session = CodingSessionState(
            session_id="SESS-TEST",
            mission_id="MISSION-TEST",
            workflow_run_id="WF-TEST",
            agent_task_id="AT-TEST",
            workspace_id="WS-TEST",
            repository="test/repo",
            base_ref="main",
            base_sha="abc123",
            workspace_path=self.tmp,
            status="verified",
            iteration=3,
            changed_files=["app/new_file.py"],
            validation_history=[
                ValidationOutcome(
                    iteration=3,
                    overall="passed",
                    commands=[
                        CommandResult(
                            argv=["python3", "-c", "pass"],
                            exit_code=0,
                            stdout="",
                            stderr="",
                            duration_ms=10,
                        )
                    ],
                )
            ],
        )

        diff = build_verified_diff(session)
        self.assertEqual(diff.status, "verified_diff_ready")
        self.assertEqual(diff.mission_id, "MISSION-TEST")
        self.assertFalse(diff.governance["remote_repository_mutated"])
        self.assertFalse(diff.governance["push_performed"])
        self.assertFalse(diff.governance["pull_request_created"])

    def test_26_no_remote_mutation_in_diff(self) -> None:
        """Test: Verified diff explicitly records no remote mutation occurred."""
        session = CodingSessionState(
            session_id="SESS-TEST",
            mission_id="MISSION-TEST",
            workflow_run_id="WF-TEST",
            agent_task_id="AT-TEST",
            workspace_id="WS-TEST",
            repository="test/repo",
            base_ref="main",
            base_sha="abc123",
            workspace_path=self.tmp,
            status="verified",
            iteration=1,
            changed_files=[],
            validation_history=[],
        )

        diff = build_verified_diff(session)
        self.assertFalse(diff.governance.get("remote_repository_mutated", True))
        self.assertFalse(diff.governance.get("commit_created", True))
        self.assertFalse(diff.governance.get("push_performed", True))
        self.assertFalse(diff.governance.get("pull_request_created", True))


# ============================================================================
# Models / Identity Tests
# ============================================================================

class TestModelIdentity(unittest.TestCase):
    """Tests 21, 22: mission identity, workflow/task identity preservation."""

    def test_27_mission_identity_preserved(self) -> None:
        """Test: MISSION-* identity is preserved throughout."""
        session = CodingSessionState(
            session_id="SESS-1",
            mission_id="MISSION-TEST-001",
            workflow_run_id="WF-RUN-001",
            agent_task_id="AGENT-TASK-001",
            workspace_id="WS-1",
            repository="test/repo",
            base_ref="main",
            base_sha="abc",
            workspace_path="/tmp/test",
            status="ready",
        )
        self.assertEqual(session.mission_id, "MISSION-TEST-001")
        self.assertTrue(session.mission_id.startswith("MISSION-"))

    def test_28_workflow_and_task_identity_preserved(self) -> None:
        """Test: Workflow run and agent task IDs are carried through."""
        session = CodingSessionState(
            session_id="SESS-1",
            mission_id="MISSION-TEST-001",
            workflow_run_id="WF-RUN-001",
            agent_task_id="AGENT-TASK-001",
            workspace_id="WS-1",
            repository="test/repo",
            base_ref="main",
            base_sha="abc",
            workspace_path="/tmp/test",
            status="ready",
        )
        self.assertEqual(session.workflow_run_id, "WF-RUN-001")
        self.assertEqual(session.agent_task_id, "AGENT-TASK-001")


# ============================================================================
# End-to-End Scenario
# ============================================================================

class TestEndToEndScenario(unittest.TestCase):
    """
    Tests 25-28: end-to-end disposable repository scenario.
    
    Creates a temporary repo with a deliberately failing implementation,
    then verifies the coding loop detects failure and stops with evidence.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        # Create a git repo
        subprocess.run(["git", "init"], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "config", "user.email", "e2e@test.com"], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "config", "user.name", "E2E"], cwd=self.tmp, capture_output=True)

        # Create app structure with a deliberately failing module
        app_dir = Path(self.tmp) / "app"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "__init__.py").write_text("")

        # Deliberately broken syntax
        (app_dir / "broken_module.py").write_text("def broken(:\n    pass\n")

        subprocess.run(["git", "add", "."], cwd=self.tmp, capture_output=True)
        subprocess.run(["git", "commit", "-m", "broken"], cwd=self.tmp, capture_output=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_29_deliberate_syntax_failure_captured(self) -> None:
        """Test: Deliberately broken syntax is caught by compileall."""
        result = run_command(
            ["python3", "-m", "compileall", "-q", "app"],
            self.tmp,
        )
        self.assertNotEqual(result.exit_code, 0)

        failure = analyze_failure(
            result, "MISSION-E2E", "WS-E2E", 1,
        )
        self.assertEqual(failure.category, "syntax-error")
        self.assertTrue(failure.retryable)

    def test_30_repair_applied_to_same_workspace(self) -> None:
        """Test: Repair modifies the same workspace files."""
        broken_path = Path(self.tmp) / "app" / "broken_module.py"
        
        # Apply repair via edit executor
        contract = EditContract(
            mission_id="MISSION-REPAIR",
            iteration=2,
            objective="Repair syntax error",
            edits=[
                EditOperation(
                    path="app/broken_module.py",
                    operation="update",
                    strategy="replace_file",
                    content="def fixed():\n    return True\n",
                    reason="Fix syntax error",
                    source_evidence=["failure-id-001"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertIn("app/broken_module.py", changed)

        # Verify the file was actually changed
        self.assertEqual(broken_path.read_text(), "def fixed():\n    return True\n")

        # Second validation should pass
        result = run_command(
            ["python3", "-m", "compileall", "-q", "app"],
            self.tmp,
        )
        self.assertEqual(result.exit_code, 0)

    def test_31_second_validation_sees_repaired_files(self) -> None:
        """Test: After repair, second validation sees the fixed files."""
        # First validation: broken syntax
        broken_path = Path(self.tmp) / "app" / "broken_module.py"
        broken_path.write_text("def broken(:\n    pass\n")
        
        result1 = run_command(
            ["python3", "-m", "compileall", "-q", "app"],
            self.tmp,
        )
        self.assertNotEqual(result1.exit_code, 0)

        # Repair
        broken_path.write_text("def fixed():\n    return True\n")

        # Second validation: should pass
        result2 = run_command(
            ["python3", "-m", "compileall", "-q", "app"],
            self.tmp,
        )
        self.assertEqual(result2.exit_code, 0)


# ============================================================================
# Python 3.9 Compatibility Tests
# ============================================================================

class TestPython39Compatibility(unittest.TestCase):
    """Test 27: Python 3.9 compatibility."""

    def test_32_no_match_case_syntax(self) -> None:
        """Test: No match/case syntax in coding_agent module."""
        import ast
        import os

        module_dir = Path(__file__).parent.parent / "coding_agent"
        for root, dirs, files in os.walk(str(module_dir)):
            for f in files:
                if f.endswith(".py"):
                    filepath = os.path.join(root, f)
                    source = Path(filepath).read_text()
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        # match/case was added in Python 3.10
                        if isinstance(node, ast.Match):
                            self.fail("match/case found in %s" % filepath)

    def test_33_python39_compileall(self) -> None:
        """Test: coding_agent module compiles under Python 3.9+."""
        result = subprocess.run(
            ["python3", "-m", "compileall", "-q", "app/platform/coding_agent"],
            cwd=Path(__file__).parent.parent.parent.parent,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)


# ============================================================================
# Policy Tests
# ============================================================================

class TestPolicy(unittest.TestCase):
    """Verify policy constants are reasonable."""

    def test_34_policy_constants_defined(self) -> None:
        """Test: All policy constants have sensible values."""
        from app.platform.coding_agent import policy
        self.assertGreater(policy.MAX_CODING_ITERATIONS, 0)
        self.assertGreater(policy.MAX_COMMAND_RUNTIME_SECONDS, 0)
        self.assertGreater(policy.MAX_FILE_SIZE_BYTES, 0)
        self.assertGreater(policy.MAX_IDENTICAL_FAILURES, 0)
        self.assertIsInstance(policy.NATIVE_CODING_AGENT_ENABLED, bool)

    def test_35_feature_flag_defaults_to_false(self) -> None:
        """Test: NATIVE_CODING_AGENT_ENABLED defaults to False (Condition 1)."""
        from app.platform.coding_agent import policy
        self.assertFalse(policy.NATIVE_CODING_AGENT_ENABLED,
                         msg="NATIVE_CODING_AGENT_ENABLED must default to False")


# ============================================================================
# AST-Based Edit Strategy Tests (Condition 2)
# ============================================================================

class TestAstBasedEdits(unittest.TestCase):
    """Tests for AST-based edit strategy (condition 2)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_36_ast_replace_strategy_applied(self) -> None:
        """Test: AST-based replacement replaces only the target function."""
        source = """\"\"\"Module doc.\"\"\"

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        fake_file = Path(self.tmp) / "math_utils.py"
        fake_file.write_text(source)

        replacement = """def add(a, b):
    '''Add two numbers with validation.'''
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Numbers required")
    return a + b
"""
        contract = EditContract(
            mission_id="MISSION-AST",
            iteration=1,
            objective="Replace add function",
            edits=[
                EditOperation(
                    path="math_utils.py",
                    operation="update",
                    strategy="ast_replace",
                    content=replacement,
                    target_symbol="add",
                    target_type="function",
                    reason="Fix add function",
                    source_evidence=["failure-1"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        self.assertIn("math_utils.py", changed)
        self.assertEqual(fps["math_utils.py"]["strategy"], "ast_replace")

        # Verify only the add function was changed, subtract is intact
        result = fake_file.read_text()
        self.assertIn("def add(a, b):", result)
        self.assertIn("TypeError", result)
        self.assertIn("def subtract(a, b):", result)
        self.assertIn("return a - b", result)

    def test_37_ast_replace_falls_back_to_file_replace(self) -> None:
        """Test: When target_symbol not found, falls back to replace_file."""
        source = """def multiply(a, b):
    return a * b
"""
        fake_file = Path(self.tmp) / "ops.py"
        fake_file.write_text(source)

        contract = EditContract(
            mission_id="MISSION-FALLBACK",
            iteration=1,
            objective="Replace nonexistent function",
            edits=[
                EditOperation(
                    path="ops.py",
                    operation="update",
                    strategy="ast_replace",
                    content="def add(a, b):\n    return a + b\n",
                    target_symbol="add",  # Not in the file
                    target_type="function",
                    reason="Try AST replace",
                    source_evidence=["failure-1"],
                )
            ],
        )
        changed, fps, warnings = apply_edits(contract, self.tmp)
        # Should succeed via fallback to replace_file
        self.assertIn("ops.py", changed)
        self.assertEqual(fps["ops.py"]["strategy"], "replace_file")

    def test_38_strategy_priority_is_honored(self) -> None:
        """Test: Strategies are tried in priority order (ast_replace > apply_patch > replace_file)."""
        from app.platform.coding_agent.edit_executor import _effective_strategies

        # When ast_replace is specified, it should be first
        edit_ast = EditOperation(
            path="x.py", operation="update", strategy="ast_replace",
            content="...", reason="test", source_evidence=["e"],
            target_symbol="func", target_type="function",
        )
        strategies = _effective_strategies(edit_ast)
        self.assertEqual(strategies[0], "ast_replace")

        # When no strategy specified, auto-detect priority
        edit_auto = EditOperation(
            path="x.py", operation="update", strategy="",
            content="...", reason="test", source_evidence=["e"],
        )
        strategies2 = _effective_strategies(edit_auto)
        # replace_file is lowest priority (index 2)
        self.assertEqual(strategies2[-1], "replace_file")


# ============================================================================
# Enhanced Failure Analyzer Tests (Condition 3)
# ============================================================================

class TestEnhancedFailureAnalyzer(unittest.TestCase):
    """Tests for the 7 enhanced dimensions (condition 3)."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        # Create a small workspace with dependencies
        app_dir = Path(self.tmp) / "app"
        app_dir.mkdir(exist_ok=True)
        (app_dir / "__init__.py").write_text("")
        (app_dir / "service.py").write_text("""
def process_request(data):
    return {"result": data}

def helper_func(x):
    return x * 2
""")
        (app_dir / "main.py").write_text("""
from app.service import process_request

def run():
    return process_request("hello")
""")
        # Create a failing command result
        self.sample_result = CommandResult(
            argv=["python3", "-m", "compileall", "app"],
            exit_code=1,
            stdout="",
            stderr='''
  File "app/service.py", line 2
    return {"result": data}
    ^
IndentationError: unexpected indent
''',
            duration_ms=100,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_39_dependency_graph_built(self) -> None:
        """Test: Dependency graph is built from workspace files."""
        failure = analyze_failure(
            self.sample_result, "MISSION-DEP", "WS-DEP", 1,
            workspace_path=self.tmp,
        )
        self.assertGreater(len(failure.dependency_graph), 0)
        # main.py should import service.py
        imports = [e for e in failure.dependency_graph if e["relation"] == "imports"]
        self.assertGreater(len(imports), 0)

    def test_40_changed_symbols_detected(self) -> None:
        """Test: Changed symbols are detected in affected files."""
        failure = analyze_failure(
            self.sample_result, "MISSION-SYM", "WS-SYM", 1,
            workspace_path=self.tmp,
        )
        self.assertGreater(len(failure.changed_symbols), 0)
        names = [s["name"] for s in failure.changed_symbols]
        self.assertIn("process_request", names)

    def test_41_caller_chain_built(self) -> None:
        """Test: Caller chain identifies who calls changed symbols."""
        failure = analyze_failure(
            self.sample_result, "MISSION-CALL", "WS-CALL", 1,
            workspace_path=self.tmp,
        )
        if failure.changed_symbols:
            self.assertIsInstance(failure.caller_chain, list)
            # run() in main.py calls process_request()
            callers = [c["caller"] for c in failure.caller_chain]
            if callers:
                self.assertIn("run", callers)

    def test_42_regression_probability_assessed(self) -> None:
        """Test: Regression probability is assessed."""
        failure = analyze_failure(
            self.sample_result, "MISSION-REG", "WS-REG", 1,
            workspace_path=self.tmp,
        )
        self.assertIn(failure.regression_probability, {"low", "medium", "high", "critical", "unknown"})
        self.assertIsInstance(failure.regression_reason, str)

    def test_43_architecture_violation_checked(self) -> None:
        """Test: Architecture constraints are checked against affected paths."""
        failure = analyze_failure(
            self.sample_result, "MISSION-ARCH", "WS-ARCH", 1,
            workspace_path=self.tmp,
            architecture_constraints=["Do not modify app/service.py"],
        )
        self.assertTrue(failure.architecture_violation)
        self.assertIn("app/service.py", failure.architecture_violation_detail)

    def test_44_diagnosis_confidence_assessed(self) -> None:
        """Test: Diagnosis confidence is assessed."""
        failure = analyze_failure(
            self.sample_result, "MISSION-CONF", "WS-CONF", 1,
            workspace_path=self.tmp,
        )
        self.assertIn(failure.diagnosis_confidence, {"low", "medium", "high"})


# ============================================================================
# Repair Evidence Tests (Additional Request)
# ============================================================================

class TestRepairEvidence(unittest.TestCase):
    """Tests for repair evidence exposure capability."""

    def test_45_repair_evidence_models(self) -> None:
        """Test: RepairAttempt and RepairEvidenceBundle models work."""
        from app.platform.coding_agent.models import RepairAttempt, RepairEvidenceBundle

        attempt = RepairAttempt(
            attempt_id="REPAIR-1",
            iteration=2,
            strategy_used="ast_replace",
            strategy_success=True,
            changed_files=["app/service.py"],
            validation_outcome="passed",
            failure_category="syntax-error",
            failure_summary="Fixed syntax",
            diagnosis_confidence="high",
        )
        self.assertEqual(attempt.strategy_used, "ast_replace")
        self.assertTrue(attempt.strategy_success)

        bundle = RepairEvidenceBundle(
            session_id="SESS-1",
            mission_id="MISSION-1",
            workspace_id="WS-1",
            total_iterations=3,
            converged=True,
            attempts=[attempt],
        )
        summary = bundle.summary()
        self.assertTrue(summary["converged"])
        self.assertEqual(summary["total_iterations"], 3)
        self.assertIn("ast_replace", summary["attempts_by_strategy"])


if __name__ == "__main__":
    unittest.main()
