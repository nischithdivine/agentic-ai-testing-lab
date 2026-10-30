"""
06 - RAG agent: Contextual Precision, Contextual Recall, Faithfulness,
     Answer Relevancy + G-Eval Correctness (traced dataset)

What it checks : the right documents are retrieved, the answer sticks to them,
                 and the answer is actually correct.
Why Correctness: RAG metrics compare the answer with the retrieved documents, not with
                 the truth. If a document is wrong, a wrong answer still passes them.
Defect found   : DEF-02 (express shipping $15 in the knowledge base vs $12.99 elsewhere).
Agent          : rag_agent.py (retrieved documents are sent to DeepEval as retrieval_context)
Run            : python evals/06_rag.py
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
from deepeval.metrics import (ContextualPrecisionMetric, ContextualRecallMetric,
                              FaithfulnessMetric, AnswerRelevancyMetric, GEval)
from deepeval.test_case import SingleTurnParams
from deepeval.tracing import observe, update_current_trace
from rag_agent import rag_support_agent as _rag_support_agent


# ---- 2. ASK ----
@observe(name="rag_support_agent")
def rag_support_agent(user_input: str) -> str:
    golden = get_current_golden()
    if golden:
        if golden.expected_tools:
            update_current_trace(expected_tools=golden.expected_tools)
        if golden.expected_output:
            update_current_trace(expected_output=golden.expected_output)
    return _rag_support_agent(user_input)


# ---- 3. SHEET ----
dataset = EvaluationDataset(goldens=[
    Golden(input="What is the return policy for electronics?",
           expected_output="Electronics can be returned within 15 days of delivery if unopened "
                           "and in original packaging. Refunds take 5-7 business days."),
    Golden(input="Can I return clothing after 30 days?",
           expected_output="No. Clothing can only be returned within 30 days of delivery, "
                           "with original tags attached, unworn and unwashed."),
    # Data-consistency check: policies.txt and the MCP server both say $12.99
    Golden(input="How much does express shipping cost and how long does it take?",
           expected_output="Express shipping takes 1-2 business days and costs $12.99."),
])

# ---- 4. METRICS ----
precision = ContextualPrecisionMetric(threshold=0.7, model="gpt-4o")
recall = ContextualRecallMetric(threshold=0.7, model="gpt-4o")
faithfulness = FaithfulnessMetric(threshold=0.7, model="gpt-4o")
relevancy = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o")
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
        metrics=[precision, recall, faithfulness, relevancy, correctness],
        display_config=DisplayConfig(truncate_passing_cases=False)):
    rag_support_agent(golden.input)
