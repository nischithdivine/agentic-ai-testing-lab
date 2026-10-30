"""
01 - Task Completion (single test case)

What it checks : did the support agent finish the customer's job?
Pattern        : single test case (LLMTestCase + evaluate)
Agent          : agent_instrumented.py (original support agent)
Run            : python evals/01_task_completion.py
"""

# ---- 0. SETUP ----
import truststore
truststore.inject_into_ssl()  # only needed on networks that inspect SSL traffic
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root

# ---- 1. IMPORTS ----
from deepeval.evaluate import evaluate
from deepeval.metrics import TaskCompletionMetric
from deepeval.test_case import LLMTestCase
from agent_instrumented import support_agent

# ---- 2. ASK ----
question = "Where is my order ORD-1042?"
answer = support_agent(question)

# ---- 3. SHEET ----
test_case = LLMTestCase(input=question, actual_output=answer)

# ---- 4. METRICS ----
task_completion = TaskCompletionMetric(threshold=0.7, model="gpt-4o")

# ---- 5. RUN ----
evaluate(test_cases=[test_case], metrics=[task_completion])
