"""
Eval template for agent benchmark harness.

Copy this file for each new eval and customize the assertions.
Tag with pytest markers for category filtering.

Usage:
    pytest evals/ -m "verification"          # run only verification evals
    pytest evals/ -m "not slow"              # skip slow evals
    pytest evals/ --model gpt-4o             # test specific model
"""

import pytest
from typing import List, Dict, Any

# --- Test Configuration ---

# Markers: tool_use, verification, efficiency, correctness, planning
pytestmark = [pytest.mark.verification, pytest.mark.correctness]

# --- Eval Definition ---

TASK = """
{task_description}
"""

EXPECTED_BEHAVIORS = [
    "agent_runs_tests_before_submit",
    "agent_reads_test_output",
    "agent_checks_edge_cases",
]

# --- Assertions ---

def test_correctness(agent_trace: str, agent_result: Any):
    """
    Did the agent fully solve the task?
    
    Customize based on task:
    - Check file contents match expected
    - Check specific functions exist and work
    - Check output matches ground truth
    """
    # Example: check a file was created with expected content
    # assert "auth.ts" in agent_result.modified_files
    # assert "redirect" in agent_result.file_contents["auth.ts"]
    pass


def test_efficiency(agent_trace: str, agent_metrics: Dict[str, Any]):
    """
    Was the solution efficient?
    
    Check against thresholds:
    - Max turns for this task type
    - Max tool calls
    - Parallelization opportunities taken
    """
    # Example thresholds
    MAX_TURNS = 15
    MAX_TOOL_CALLS = 12
    
    assert agent_metrics["turns"] <= MAX_TURNS, (
        f"Agent took {agent_metrics['turns']} turns, max allowed: {MAX_TURNS}"
    )
    assert agent_metrics["tool_calls"] <= MAX_TOOL_CALLS, (
        f"Agent made {agent_metrics['tool_calls']} tool calls, max allowed: {MAX_TOOL_CALLS}"
    )


def test_tool_use(agent_trace: str, agent_metrics: Dict[str, Any]):
    """
    Did the agent use tools effectively?
    
    Check for:
    - No edit loops (same file edited > N times)
    - Right tools selected
    - Parallelization where possible
    """
    # Example: check no file was edited more than 3 times
    for file, edit_count in agent_metrics["file_edit_counts"].items():
        assert edit_count <= 3, (
            f"File '{file}' was edited {edit_count} times — possible loop"
        )
    
    # Example: check parallelization
    assert agent_metrics["parallelized_calls"] >= 1, (
        "Agent missed opportunity to parallelize independent tool calls"
    )


def test_verification(agent_trace: str, agent_metrics: Dict[str, Any]):
    """
    Did the agent verify its work?
    
    Check for:
    - Tests were run
    - Output was read
    - Spec was compared
    """
    trace_lower = agent_trace.lower()
    
    # Check test execution
    test_commands = ["pytest", "npm test", "cargo test", "go test", "test("]
    ran_tests = any(cmd in agent_trace for cmd in test_commands)
    assert ran_tests, "Agent did not run any tests"
    
    # Check output was read (not just command executed)
    read_output_indicators = [
        "test result", "passing", "failing", "error", "output shows"
    ]
    read_output = any(ind in trace_lower for ind in read_output_indicators)
    assert read_output, "Agent may have run tests but did not read/mention output"


# --- LLM-as-Judge Helper ---

def llm_judge_correctness(task: str, agent_output: str, judge_model: str = "gpt-4o") -> float:
    """
    Use an LLM to judge correctness semantically.
    
    Returns score from 0.0 to 1.0.
    """
    prompt = f"""You are grading an AI agent's work.

Task: {task}

Agent output:
{agent_output}

Rate correctness from 0.0 to 1.0:
- 1.0 = fully correct, all requirements met
- 0.5 = partially correct, significant gaps
- 0.0 = completely wrong

Respond with ONLY a number."""
    
    # Implementation: call judge_model API here
    # return call_llm(judge_model, prompt, temperature=0.0)
    pass


# --- Fixtures (provided by harness) ---

@pytest.fixture
def agent_trace() -> str:
    """Full text of the agent session trace."""
    # Provided by benchmark harness
    pass

@pytest.fixture
def agent_result() -> Any:
    """Structured result object with file changes, outputs, etc."""
    # Provided by benchmark harness
    pass

@pytest.fixture
def agent_metrics() -> Dict[str, Any]:
    """Metrics dict with turns, tool_calls, file_edit_counts, etc."""
    # Provided by benchmark harness
    pass
