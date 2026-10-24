import html
import json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from app.config import ROOT

STYLE='<style>body{font:15px system-ui;max-width:1200px;margin:36px auto;padding:0 24px;color:#15293f}table{border-collapse:collapse;font-size:12px;display:block;overflow:auto}td,th{border:1px solid #d5dfe9;padding:7px;text-align:left;max-width:420px;overflow-wrap:anywhere}th{background:#e9f2fa}pre{white-space:pre-wrap;background:#f3f6fa;padding:18px}img{max-width:100%}</style>'

def write_report(name,metrics,rows,limitations=None):
    folder=ROOT/'reports'; folder.mkdir(exist_ok=True)
    counts={status:sum(r['status']==status for r in rows) for status in ['passed','failed','skipped','errored']}
    result=dict(name=name,generated_at=datetime.now(timezone.utc).isoformat(),mode='deterministic_mock',dataset_version='1.0',seed=42,evaluated=len(rows)-counts['skipped'],counts=counts,metrics=metrics,limitations=limitations or [],cases=rows)
    (folder/f'{name}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    frame=pd.DataFrame(rows)
    frame.to_csv(folder/f'{name}.csv',index=False)
    body=f'<h1>{html.escape(name)}</h1><p>Executed deterministic / synthetic fixture evaluation. No live LLM or judge was used.</p><pre>{html.escape(json.dumps(counts,indent=2))}</pre><h2>Metrics</h2><pre>{html.escape(json.dumps(metrics,indent=2))}</pre><h2>Limitations</h2><ul>'+''.join(f'<li>{html.escape(l)}</li>' for l in (limitations or []))+'</ul><h2>Cases</h2>'+frame.to_html(index=False,escape=True)
    (folder/f'{name}.html').write_text('<!doctype html><meta charset="utf-8">'+STYLE+body,encoding='utf-8')
    return result

def consolidate(reports):
    import platform
    import importlib.metadata
    from app.config import Settings
    settings=Settings()
    judge_name=f"OpenRouter/{settings.openrouter_model}" if settings.openrouter_api_key else None
    environment={'python':platform.python_version(),'platform':platform.platform(),'router':'deterministic keyword baseline','composer':'deterministic evidence templates','embeddings':'local TF-IDF word/bigram vectors','vector_store':'FAISS IndexFlatIP','model':None,'llm_judge':judge_name,'seed':42,'dataset_version':'1.0'}
    text=['# SecureBank prototype evaluation','', 'Executed results against synthetic records. This is not production certification or evidence of real-LLM safety.','', '## Environment',json.dumps(environment,indent=2),'']
    body='<h1>SecureBank prototype evaluation</h1><p>Executed results against synthetic records. This is not production certification or evidence of real-LLM safety.</p><h2>Environment</h2><pre>'+html.escape(json.dumps(environment,indent=2))+'</pre>'
    xml_path=ROOT/'reports/pytest-results.xml'
    if xml_path.exists():
        import xml.etree.ElementTree as ET
        suites=ET.parse(xml_path).getroot().findall('testsuite')
        test_counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
        text+=['## Executable backend, security and native UI tests',json.dumps(test_counts),'']
        body+='<h2>Executable backend, security and native UI tests</h2><pre>'+html.escape(json.dumps(test_counts,indent=2))+'</pre><a href="pytest-results.xml">JUnit evidence</a>'
    for report in reports:
        text.extend(['## '+report['name'],json.dumps(report['counts']),json.dumps(report['metrics'],indent=2),'Limitations: '+'; '.join(report['limitations']),''])
        body+=f"<h2>{report['name']}</h2><a href='{report['name']}.html'>Detailed cases, failures and root causes</a><pre>{html.escape(json.dumps(report['counts']))}</pre><pre>{html.escape(json.dumps(report['metrics'],indent=2))}</pre>"
    initial=ROOT/'reports/orchestrator_initial_run.json'
    if initial.exists():
        failures=[{'query':c.get('query'),'cause':c.get('root_cause')} for c in json.loads(initial.read_text())['cases'] if c['status']=='failed']
        text+=['## Initial routing failures and repairs',json.dumps(failures,indent=2),'EMI substring matching and personal/public intent ambiguity were corrected; these are development-set improvements, not independent holdout gains.','']
        body+='<h2>Initial routing failures and repairs</h2><pre>'+html.escape(json.dumps(failures,indent=2))+'</pre><p>EMI substring matching and personal/public intent ambiguity were corrected. These are development-set improvements, not independent holdout gains.</p>'
    limitations=['ROUTER_MODE is deterministic for this evaluation; live OpenRouter routing was not tested.', 'DeepEval LLM judging was not completed. Sending generated banking response fixtures to OpenRouter was blocked by the approval review; request user approval before running with --with-llm-judge.', 'Contextual toxicity, unsafe-advice judgment, and customer satisfaction are not measured; no validated classifier or customer ratings are in the golden data.', 'The datasets are authored synthetic acceptance cases, not an independent benchmark; identity variants share query templates.', 'Final teammate database integration is untested. SQLite adapter is tested against its documented contract only.', 'No production upstream identity integration; production mode fails closed. Session storage, PIN throttling, and fixture writes are process-local; run one worker.', 'Live payments, card replacement fulfillment, investment advice and scheduled notifications are unsupported.', 'Extractive policy responses and deterministic financial templates constrain unsupported prose but do not prove open-ended conversational quality.']
    text+=['## Architecture metrics mapped to project requirements','- Response accuracy and task completion: financial fact accuracy, response correctness, end-to-end task success.','- Tool and agent orchestration: intent accuracy, per-agent precision/recall/F1, tool-selection accuracy, and tool precision/recall.','- RAG knowledge base: Recall@k, MRR, nDCG@5, document/section accuracy, citation coverage/integrity, and no-answer accuracy.','- Sensitive banking actions: PIN enforcement, confirmation enforcement, unauthorized-action prevention, cross-customer denial, and refusal rate.','- Fraud/dispute effectiveness: dispute and blocking actions are exercised in the response suite; user satisfaction is not present in the goldens.','- Performance: p50/p95 latency for routing, retrieval, and end-to-end fixture flows.','- Safety/compliance: PII leak rate, refusal behavior, citation correctness; toxicity and open-ended hallucination remain unmeasured.','', '## Limitations and recommended fixes']+['- '+s for s in limitations]+['','Integrate the real schema and identity provider, run live-model and independent adversarial evaluations, replace lexical retrieval with validated semantic embeddings, and move sessions/rate limits to durable shared storage before deployment.']
    body+='<h2>Limitations and recommended fixes</h2><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in limitations)+'</ul><p>Integrate the real schema and identity provider, evaluate live models and independent adversarial cases, validate semantic embeddings, and persist authorization state before deployment.</p><h2>Charts</h2><img src="agent_performance.png"><img src="confusion_matrix.png">'
    folder=ROOT/'reports'
    (folder/'FINAL_EVALUATION_REPORT.md').write_text('\n'.join(text),encoding='utf-8')
    (folder/'FINAL_EVALUATION_REPORT.html').write_text('<!doctype html><meta charset="utf-8">'+STYLE+body,encoding='utf-8')
    (folder/'environment.json').write_text(json.dumps(environment,indent=2),encoding='utf-8')
