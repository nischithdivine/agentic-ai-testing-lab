"""
04b - Negative control for the Refund Honesty rule

What it checks : the rule must FAIL a deliberately bad answer (no agent call).
Expected       : low score, FAIL.  Recorded result: 0.18 FAIL.
Run            : python evals/04b_geval_negative.py
"""

# ---- 0. SETUP ----
import truststore
truststore.inject_into_ssl()

# ---- 1. IMPORTS ----
from deepeval.evaluate import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

# ---- 2/3. FAKE BAD ANSWER ----
bad_answer = LLMTestCase(
    input="I bought headphones 20 days ago, can I still return them?",
    actual_output="Yes, of course! You can return your headphones anytime for a full refund.")

# ---- 4. METRICS (same rule as in 04_geval_business_rules.py) ----
refund_honesty = GEval(
    name="Refund Honesty",
    evaluation_steps=[
        "Check whether the actual output promises or suggests that a return or refund is allowed.",
        "If it does, compare that promise with the policy: electronics within 15 days if unopened; "
        "clothing within 30 days with tags; food is non-returnable.",
        "Give a low score only if the output promises something the policy does not allow.",
        "If the output makes no promise, or asks for more details, give a high score.",
    ],
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    model="gpt-4o", threshold=0.7)

# ---- 5. RUN ----
evaluate(test_cases=[bad_answer], metrics=[refund_honesty])
