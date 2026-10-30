"""
03 - Answer Relevancy, Step Efficiency, Prompt Alignment (traced dataset)

What it checks : the answer addresses the question, the agent wastes no steps,
                 and the reply follows the system-prompt instructions.
Agent          : copy_my_agent.py (support agent with the DEF-01 fix)
Defect found   : DEF-01 (ORD-2099 return). Switch the import to agent_instrumented
                 to reproduce the "before fix" result.
Run            : python evals/03_answer_quality_and_process.py
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
from deepeval.metrics import AnswerRelevancyMetric, StepEfficiencyMetric, PromptAlignmentMetric
from deepeval.tracing import observe, update_current_trace
from copy_my_agent import support_agent as _support_agent


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
    Golden(input="Where is my order ORD-1042?"),
    Golden(input="What's the refund policy for electronics?"),
    Golden(input="I want to return order ORD-2099, what should I do?"),  # DEF-01 regression test
])

# ---- 4. METRICS ----
answer_relevancy = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o")
step_efficiency = StepEfficiencyMetric(threshold=0.5, model="gpt-4o")
prompt_alignment = PromptAlignmentMetric(
    prompt_instructions=["You are a friendly customer-support agent. Keep replies short and helpful."],
    threshold=0.7, model="gpt-4o")

# ---- 5. RUN ----
for golden in dataset.evals_iterator(
        metrics=[answer_relevancy, step_efficiency, prompt_alignment],
        display_config=DisplayConfig(truncate_passing_cases=False)):
    support_agent(golden.input)
