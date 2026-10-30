"""
02 - Task Completion + Tool Correctness (traced dataset)

What it checks : the job was done AND the right tool was called.
Pattern        : @observe wrapper + EvaluationDataset of goldens + evals_iterator
Agent          : agent_instrumented.py (original support agent)
Run            : python evals/02_task_and_tool_correctness.py
Note           : Tool Correctness needs the DeepEval 4.0.4 patch described in DEF-04.
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


# ---- 2. ASK (reusable traced wrapper: passes whatever the golden contains) ----
@observe(name="support_agent")
def support_agent(user_input: str) -> str:
    golden = get_current_golden()
    if golden:
        if golden.expected_tools:
            update_current_trace(expected_tools=golden.expected_tools)
        if golden.expected_output:
            update_current_trace(expected_output=golden.expected_output)
    return _support_agent(user_input)


# ---- 3. SHEET ----
dataset = EvaluationDataset(goldens=[
    Golden(input="Where is my order ORD-1042?",
           expected_tools=[ToolCall(name="get_order_status")]),
    Golden(input="What is refund policy for electronics?",
           expected_tools=[ToolCall(name="get_refund_policy")]),
])

# ---- 4. METRICS ----
task_completion = TaskCompletionMetric(threshold=0.7, model="gpt-4o")
tool_correctness = ToolCorrectnessMetric()  # name match, no LLM needed

# ---- 5. RUN ----
for golden in dataset.evals_iterator(metrics=[task_completion, tool_correctness]):
    support_agent(golden.input)
