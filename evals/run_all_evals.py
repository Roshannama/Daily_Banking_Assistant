"""Full deterministic architecture checks plus DeepEval LLM-as-judge scoring."""
import argparse
import json
from evals.evaluate_orchestrator import evaluate as routing
from evals.evaluate_rag import evaluate as rag
from evals.evaluate_responses import evaluate as responses
from evals.report_generator import consolidate
from evals.deepeval_runner import run as deepeval
from app.config import ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-llm-judge", action="store_true",
                        help="Send synthetic golden responses to the configured OpenRouter judge")
    args = parser.parse_args()
    reports=[]
    for evaluate_suite in (routing, rag, responses):
        report = evaluate_suite(); reports.append(report)
        print(report['name'], report['counts'])
    consolidate(reports)
    if args.with_llm_judge:
        judge_report = deepeval()
        print('DeepEval:', judge_report['metrics'])
    else:
        judge_report = {
            "name": "deepeval_response_judgment", "framework": "DeepEval",
            "status": "not_run_external_transfer_requires_explicit_opt_in",
            "evaluated": 0, "metrics": {"judge_correctness_mean": None, "judge_pass_rate": None},
            "reason": "LLM judging sends generated banking response fixtures to OpenRouter. Re-run with --with-llm-judge only after approving that transfer.",
        }
        (ROOT / "reports/deepeval_report.json").write_text(json.dumps(judge_report, indent=2), encoding="utf-8")
        (ROOT / "reports/deepeval_report.md").write_text(
            "# DeepEval response evaluation\n\nNot run: LLM judging sends generated banking response fixtures to OpenRouter. "
            "Use `python -m evals.run_all_evals --with-llm-judge` after approving that data transfer.\n",
            encoding="utf-8",
        )
        print('DeepEval judge not run; see reports/deepeval_report.md')
    print('Consolidated reports written to reports/.')

if __name__=='__main__':main()
