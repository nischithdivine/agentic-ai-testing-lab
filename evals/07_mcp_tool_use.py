"""
07 - MCP tool use by the agent (traced dataset)

What it checks : when asked about shipping, the agent calls the MCP tool
                 get_shipping_options and reports the right methods and prices.
Agent          : agent_instrumented.py (loads get_shipping_options from mcp_server.py over stdio)
Run            : python evals/07_mcp_tool_use.py
"""

# ---- 0. SETUP ----
import truststore
truststore.inject_into_ssl()
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 1. IMPORTS ----
from deepeval.contextvars import get_current_golden
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.evaluate import DisplayConfig
from deepeval.metrics import ToolCorrectnessMetric, GEval
from deepeval.test_case import ToolCall, SingleTurnParams
from deepeval.tracing import observe, update_current_trace
from agent_instrumented import support_agent as _support_agent


# ---- 2. ASK ----
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
    Golden(input="What shipping options do you have?",
           expected_tools=[ToolCall(name="get_shipping_options")],
           expected_output="Standard takes 3-5 days and is free on orders over $50; "
                           "Express takes 1-2 days and costs $12.99; "
                           "Overnight arrives the next business day and costs $24.99."),
])

# ---- 4. METRICS ----
tool_correctness = ToolCorrectnessMetric()
correctness = GEval(
    name="Correctness",
    criteria=("Check whether the actual output gives the same facts as the expected output. "
              "Small wording differences are fine; missing or wrong facts, especially numbers "
              "and prices, are not."),
    evaluation_params=[SingleTurnParams.INPUT,
                       SingleTurnParams.EXPECTED_OUTPUT,
                       SingleTurnParams.ACTUAL_OUTPUT],
    model="gpt-4o", threshold=0.7)

# ---- 5. RUN ----
for golden in dataset.evals_iterator(
        metrics=[tool_correctness, correctness],
        display_config=DisplayConfig(truncate_passing_cases=False)):
    support_agent(golden.input)