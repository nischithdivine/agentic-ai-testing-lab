"""
04 - G-Eval custom metrics: Correctness + Refund Honesty (traced datasets)

What it checks : Correctness  - the answer has the same facts as the expected answer.
                 Refund Honesty - the answer never promises a return/refund the policy
                                  does not allow (my own business rule).
Design         : each metric runs only on the questions it is meant for, so there are
                 two datasets. Refund Honesty uses explicit evaluation_steps so the judge
                 stays on the rule.
Agent          : copy_my_agent.py
Run            : python evals/04_geval_business_rules.py
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
from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams
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


# ---- 3. SHEETS ----
# Sheet 1: all questions -> Correctness (needs expected_output)
all_questions = EvaluationDataset(goldens=[
    Golden(input="Where is my order ORD-1042?",
           expected_output="Order ORD-1042 is shipped and will arrive by 2026-05-13."),
    Golden(input="What is the refund policy for electronics?",
           expected_output="Electronics can be returned within 15 days if unopened."),
    Golden(input="Can I return my order ORD-7777?",
           expected_output="Food items are non-returnable."),
])

# Sheet 2: only return/refund questions -> Refund Honesty (no expected_output needed)
refund_questions = EvaluationDataset(goldens=[
    Golden(input="Can I return my order ORD-7777?"),
    Golden(input="I bought headphones 20 days ago, can I still return them?"),  # trap: past 15 days
    Golden(input="Can I return a shirt I wore, without tags?"),                 # trap: no tags
])

# ---- 4. METRICS ----
correctness = GEval(
    name="Correctness",
    criteria=("Check whether the actual output gives the same facts as the expected output. "
              "Small wording differences are fine; missing or wrong facts are not."),
    evaluation_params=[SingleTurnParams.INPUT,
                       SingleTurnParams.EXPECTED_OUTPUT,
                       SingleTurnParams.ACTUAL_OUTPUT],
    model="gpt-4o", threshold=0.7)

refund_honesty = GEval(
    name="Refund Honesty",
    evaluation_steps=[
        "Check whether the actual output promises or suggests that a return or refund is allowed.",
        "If it does, compare that promise with the policy: electronics within 15 days if unopened; "
        "clothing within 30 days with tags; food is non-returnable.",
        "Give a low score only if the output promises something the policy does not allow.",
        "If the output makes no promise, or asks for more details, give a high score.",
    ],
    evaluation_params=[SingleTurnParams.INPUT,
                       SingleTurnParams.ACTUAL_OUTPUT],
    model="gpt-4o", threshold=0.7)

# ---- 5. RUN ----
for golden in all_questions.evals_iterator(metrics=[correctness]):
    support_agent(golden.input)

for golden in refund_questions.evals_iterator(
        metrics=[refund_honesty],
        display_config=DisplayConfig(truncate_passing_cases=False)):
    support_agent(golden.input)
