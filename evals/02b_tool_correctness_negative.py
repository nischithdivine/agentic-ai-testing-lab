"""
02b - Negative control for Tool Correctness

What it checks : Tool Correctness must FAIL when the expected tool is wrong.
Expected       : Tool Correctness 0.00 (fail) while Task Completion still passes,
                 showing the two metrics measure different things.
Run            : python evals/02b_tool_correctness_negative.py
"""

# ---- 0. SETUP ----
import truststore
truststore.inject_into_ssl()
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 1. IMPORTS ----
from deepeval.contextvars import get_current_golden
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import TaskCompletionMetric, ToolCorrectnessMetric
from deepeval.test_case import ToolCall
from deepeval.tracing import observe, update_current_trace
from agent_instrumented import support_agent as _support_agent


# ---- 2. ASK ----
@observe(name="support_agent")
def support_agent(user_input: str) -> str:
    golden = get_current_golden()
    if golden and golden.expected_tools:
        update_current_trace(expected_tools=golden.expected_tools)
    return _support_agent(user_input)


# ---- 3. SHEET (deliberately wrong expected tool) ----
dataset = EvaluationDataset(goldens=[
    Golden(input="Where is my order ORD-1042?",
           expected_tools=[ToolCall(name="get_refund_policy")]),  # wrong on purpose
])

# ---- 4. METRICS ----
task_completion = TaskCompletionMetric(threshold=0.7, model="gpt-4o")
tool_correctness = ToolCorrectnessMetric()

# ---- 5. RUN ----
for golden in dataset.evals_iterator(metrics=[task_completion, tool_correctness]):
    support_agent(golden.input)
