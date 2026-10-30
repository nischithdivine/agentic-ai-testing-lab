# Defect Report

**Project:** Agentic AI Testing Lab (ShopEasy)  **Tester:** Nischith R  **Date:** 31 Oct 2026

Severity: **High** = customer gets wrong or incomplete information · **Medium** = blocks or breaks testing/setup · **Low** = minor quality issue.

---

## DEF-01: Return request for ORD-2099 gives an incomplete answer

| Field | Detail |
|---|---|
| Severity / Priority | High / P1 |
| Component | Support agent: `get_order_status` tool + system prompt |
| Found by | DeepEval trace metrics (`evals/03_answer_quality_and_process.py`) |
| Status | **Fixed** (Answer Relevancy, Step Efficiency); Prompt Alignment still failing |

**Steps to reproduce**
1. Run the support agent with: *"I want to return order ORD-2099, what should I do?"*
2. Evaluate with Answer Relevancy, Step Efficiency and Prompt Alignment.

**Expected:** the agent looks up ORD-2099, finds it is **clothing**, gets the clothing refund policy, and says it can be returned within 30 days with tags attached.

**Actual:** the agent could not tell which refund policy applied, so the answer was vague. The return request failed all three trace metrics.

**Evidence (before fix):** Answer Relevancy 0.67 · Step Efficiency 0.00 · Prompt Alignment 0.00

**Root cause (two layers)**
1. **Tool:** `get_order_status` returned only status and ETA, **not the product category**, so the agent had no way to know ORD-2099 was clothing.
2. **System prompt:** no instruction to look up the order before fetching the refund policy.

**Fix** (in `copy_my_agent.py`)
1. Tool now returns the category: `"Order ORD-2099 is Delivered. ETA: 2026-05-08. Category: clothing"`. Verified by calling the tool directly.
2. System prompt adds: *"For a return request with an order ID, first look up the order to find its product category, then get the refund policy for that category."*

Fixing only layer 1 did not change the answer; both layers were needed.

**Retest (after fix):** Answer Relevancy **1.00** (pass) · Step Efficiency **0.50** (pass at 0.5) · Prompt Alignment **0.00** (still fail)

**Open item:** Prompt Alignment still fails. Part of this looks like a harsh judge, and part is a real gap: the agent has no tool for the actual return process, so it cannot fully complete a return. Kept as a **regression test**.

**Related observation:** the agent does not know today's date, so it cannot tell whether a delivered order is still inside its 30-day window.

---

## DEF-02: Express shipping price is inconsistent across the system

| Field | Detail |
|---|---|
| Severity / Priority | High / P1 |
| Component | RAG knowledge base (`rag_agent.py`, `POLICY_DOCS`) vs MCP server (`mcp_server.py`) and `policies.txt` |
| Found by | Reading the data sources, then confirmed with DeepEval (`evals/06_rag.py`) |
| Status | **Open** |

**Steps to reproduce**
1. Ask the RAG agent: *"How much does express shipping cost and how long does it take?"*
2. Call the MCP tool `get_shipping_options`.

**Expected:** one price for express shipping everywhere. `policies.txt` and the MCP server both say **$12.99**.

**Actual:** the RAG agent answers **"Express shipping costs $15"**, because its knowledge base says $15. A customer gets a different price depending on which part of the system answers.

**Evidence**

| Metric | Score | Result |
|---|---|---|
| Contextual Precision | 1.00 | Pass |
| Contextual Recall | 1.00 | Pass (should have failed: $12.99 is not in the retrieved documents; judge missed it) |
| Faithfulness | 1.00 | Pass (answer matches the retrieved document, which is itself wrong) |
| Answer Relevancy | 1.00 | Pass |
| **G-Eval Correctness** (vs expected answer) | **0.68** | **Fail** (threshold 0.70): *"inaccurately lists the cost as $15 instead of $12.99... a critical pricing error"* |

**Root cause:** the knowledge-base document is out of date or was written separately from the policy file and the MCP tool. The agent behaves correctly; the **data** is wrong.

**Suggested fix:** keep one source of truth for prices and build both the knowledge base and the MCP tool from it. Add a deterministic check that the answer contains `$12.99`.

**Related inconsistencies found by reviewing the data (not yet covered by an automated test)**

| Topic | Knowledge base (RAG) | `policies.txt` / MCP tool |
|---|---|---|
| Standard shipping time | 5–7 business days | 3–5 business days |
| Electronics return window | 15 days **of delivery** | 15 days **of purchase** |
| Reporting damaged food | within 24 hours | damaged items: within 48 hours |

**Lessons**
- **Faithful is not the same as correct.** Faithfulness checks the answer against the retrieved documents. If the documents are wrong, a wrong answer passes.
- **Critical values need exact checks.** The wrong price failed Correctness by only 0.02 because the judge gave partial credit for the correct delivery time.

---

## DEF-03: Course `requirements.txt` is incomplete and unpinned

| Field | Detail |
|---|---|
| Severity / Priority | Medium / P2 |
| Component | Project setup |
| Found by | Fresh install on Windows |
| Status | **Fixed in this repo** (pinned `requirements.txt`) |

**Actual:**
- Running the RAG eval failed with `ImportError: cosine_similarity requires numpy to be installed`.
- `mcp`, `langchain-mcp-adapters` and `nest_asyncio` were also missing, though the support agent imports them.
- No versions were pinned, so a fresh install could pull incompatible versions.

**Fix:** `requirements.txt` now lists every package with an exact version, including `numpy==2.4.6`.

---

## DEF-04: DeepEval Tool Correctness crashes on LangChain tool messages

| Field | Detail |
|---|---|
| Severity / Priority | Medium / P2 |
| Component | DeepEval 4.0.4 (`deepeval/test_case/llm_test_case.py`, `_make_hashable`) |
| Found by | Running Tool Correctness on the traced support agent |
| Status | **Worked around** with a local patch (third-party library) |

**Actual:** `TypeError: unhashable type: 'ToolMessage'` when Tool Correctness ran.

**Root cause:** `_make_hashable` returns objects it does not recognise unchanged; LangChain's `ToolMessage` cannot be hashed.

**Workaround** (local edit in the installed library):

```python
else:
    try:
        hash(obj)
        return obj
    except TypeError:
        return str(obj)
```

**Next step:** report it to the DeepEval maintainers so it is fixed upstream.

---

## Observations (not defects)

| ID | Observation | Decision |
|---|---|---|
| OBS-01 | For *"I bought headphones 20 days ago, can I still return them?"* the agent asked for an order ID, although it had enough information to answer (electronics, past 15 days). | Low-priority helpfulness issue; track under Task Completion. Not a refund-honesty failure. |
| OBS-02 | The agent says food is non-returnable "for safety reasons". | Checked against the source: the policy text says this, so it is **not** a hallucination. |

## Test-design issues found and fixed (the test was wrong, not the agent)

| Issue | Fix |
|---|---|
| Refund Honesty was applied to an order-tracking question and failed it | Split into two datasets; Refund Honesty runs only on return/refund questions |
| ORD-7777 golden expected details the customer did not need (failed 0.61, then 0.60) | Simplified the expected answer to the key fact: food is non-returnable |
| Refund Honesty failed an answer that made no promise (judge drifted beyond the rule) | Replaced one-line criteria with explicit `evaluation_steps`; negative control still fails at 0.18 |
