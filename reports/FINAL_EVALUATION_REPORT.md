# SecureBank prototype evaluation

Executed results against synthetic records. This is not production certification or evidence of real-LLM safety.

## Environment
{
  "python": "3.12.10",
  "platform": "Windows-11-10.0.22621-SP0",
  "router": "deterministic keyword baseline",
  "composer": "deterministic evidence templates",
  "embeddings": "local TF-IDF word/bigram vectors",
  "vector_store": "FAISS IndexFlatIP",
  "model": null,
  "llm_judge": "OpenRouter/nvidia/nemotron-3.5-lightning:free",
  "seed": 42,
  "dataset_version": "1.0"
}

## Executable backend, security and native UI tests
{"tests": 45, "failures": 0, "errors": 0, "skipped": 0}

## orchestrator_eval
{"passed": 120, "failed": 0, "skipped": 0, "errored": 0}
{
  "intent_accuracy": 1.0,
  "per_agent": {
    "account": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 30
    },
    "payments": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 18
    },
    "cards": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 18
    },
    "loans": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 18
    },
    "fraud": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 18
    },
    "knowledge": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 24
    },
    "unsupported": {
      "precision": 1.0,
      "recall": 1.0,
      "f1": 1.0,
      "support": 12
    }
  },
  "macro_f1": 1.0,
  "tool_selection_accuracy": 1.0,
  "tool_precision": 1.0,
  "tool_recall": 1.0,
  "rag_routing_accuracy": 1.0,
  "pin_detection_recall": 1.0,
  "confirmation_detection_recall": 1.0,
  "unsupported_detection_recall": 1.0,
  "multi_agent_routing_accuracy": 1.0,
  "p50_ms": 0.024100008886307478,
  "p95_ms": 0.04536501364782444,
  "confusion_matrix": {
    "labels": [
      "account",
      "payments",
      "cards",
      "loans",
      "fraud",
      "knowledge",
      "unsupported",
      "mixed"
    ],
    "values": [
      [
        24,
        0,
        0,
        0,
        0,
        0,
        0,
        0
      ],
      [
        0,
        12,
        0,
        0,
        0,
        0,
        0,
        0
      ],
      [
        0,
        0,
        18,
        0,
        0,
        0,
        0,
        0
      ],
      [
        0,
        0,
        0,
        12,
        0,
        0,
        0,
        0
      ],
      [
        0,
        0,
        0,
        0,
        12,
        0,
        0,
        0
      ],
      [
        0,
        0,
        0,
        0,
        0,
        12,
        0,
        0
      ],
      [
        0,
        0,
        0,
        0,
        0,
        0,
        12,
        0
      ],
      [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        18
      ]
    ]
  }
}
Limitations: Deterministic baseline only; not real LLM routing.; Synthetic acceptance queries are not an independent holdout.

## rag_eval
{"passed": 67, "failed": 0, "skipped": 0, "errored": 0}
{
  "recall_at_1": 0.9568965517241379,
  "recall_at_3": 1.0,
  "recall_at_5": 1.0,
  "precision_at_5": 0.20344827586206898,
  "mrr": 0.9827586206896551,
  "ndcg_at_5": 0.9872734397783262,
  "document_top1_accuracy": 0.9655172413793104,
  "section_chunk_top1_accuracy": 0.9655172413793104,
  "expected_citation_in_top3": 1.0,
  "citation_source_integrity": 1.0,
  "no_answer_detection_accuracy": 1.0,
  "extractive_answer_supported_claim_rate": 1.0,
  "answer_completeness_proxy_recall3": 1.0,
  "unsupported_source_rate": 0.0,
  "p50_ms": 0.23510001483373344,
  "p95_ms": 5.340020003495727
}
Limitations: TF-IDF lexical embeddings with FAISS; semantic paraphrases can fail.; Source integrity checks provenance, not semantic answer correctness.; Answer completeness is a gold-chunk recall proxy, not a contextual judge score.; Adversarial-case latency includes rebuilding the isolated test index.

## response_safety_eval
{"passed": 180, "failed": 0, "skipped": 4, "errored": 0}
{
  "financial_fact_accuracy": 1.0,
  "answer_correctness": 1.0,
  "supported_expected_fact_rate": 1.0,
  "expected_fact_error_rate": 0.0,
  "pii_leakage_rate": 0.0,
  "cross_customer_denial_success": 1.0,
  "pin_enforcement_rate": 1.0,
  "confirmation_enforcement_rate": 1.0,
  "unauthorized_action_prevention_rate": 1.0,
  "citation_correctness": 1.0,
  "appropriate_refusal_rate": 1.0,
  "end_to_end_task_success": 1.0,
  "toxicity_rate": null,
  "unsafe_response_rate": null,
  "open_ended_hallucination_rate": null,
  "p50_ms": 53.90015000011772,
  "p95_ms": 56.20678501145448
}
Limitations: 180 synthetic scenarios share 18 query templates across ten customers.; Financial checks compare authored expected facts with evidence and rendered monetary values.; PII metric checks identity isolation and credential leakage, not all possible sensitive strings.; Authorization negative and expired-grant cases are separately executed in pytest security suite.; Toxicity, contextual unsafe advice, and open-ended hallucination are not measured; no judge is configured.

## Initial routing failures and repairs
[
  {
    "query": "What is left after paying bills?",
    "cause": "Routing mismatch: agents, tools, rag, pin, intent"
  },
  {
    "query": "List my reminders",
    "cause": "Routing mismatch: agents, tools, intent"
  },
  {
    "query": "My outstanding loan balance",
    "cause": "Routing mismatch: agents, tools, intent"
  },
  {
    "query": "Check payment status and explain why",
    "cause": "Routing mismatch: agents, tools, pin, intent"
  }
]
EMI substring matching and personal/public intent ambiguity were corrected; these are development-set improvements, not independent holdout gains.

## Architecture metrics mapped to project requirements
- Response accuracy and task completion: financial fact accuracy, response correctness, end-to-end task success.
- Tool and agent orchestration: intent accuracy, per-agent precision/recall/F1, tool-selection accuracy, and tool precision/recall.
- RAG knowledge base: Recall@k, MRR, nDCG@5, document/section accuracy, citation coverage/integrity, and no-answer accuracy.
- Sensitive banking actions: PIN enforcement, confirmation enforcement, unauthorized-action prevention, cross-customer denial, and refusal rate.
- Fraud/dispute effectiveness: dispute and blocking actions are exercised in the response suite; user satisfaction is not present in the goldens.
- Performance: p50/p95 latency for routing, retrieval, and end-to-end fixture flows.
- Safety/compliance: PII leak rate, refusal behavior, citation correctness; toxicity and open-ended hallucination remain unmeasured.

## Limitations and recommended fixes
- ROUTER_MODE is deterministic for this evaluation; live OpenRouter routing was not tested.
- DeepEval LLM judging was not completed. Sending generated banking response fixtures to OpenRouter was blocked by the approval review; request user approval before running with --with-llm-judge.
- Contextual toxicity, unsafe-advice judgment, and customer satisfaction are not measured; no validated classifier or customer ratings are in the golden data.
- The datasets are authored synthetic acceptance cases, not an independent benchmark; identity variants share query templates.
- Final teammate database integration is untested. SQLite adapter is tested against its documented contract only.
- No production upstream identity integration; production mode fails closed. Session storage, PIN throttling, and fixture writes are process-local; run one worker.
- Live payments, card replacement fulfillment, investment advice and scheduled notifications are unsupported.
- Extractive policy responses and deterministic financial templates constrain unsupported prose but do not prove open-ended conversational quality.

Integrate the real schema and identity provider, run live-model and independent adversarial evaluations, replace lexical retrieval with validated semantic embeddings, and move sessions/rate limits to durable shared storage before deployment.