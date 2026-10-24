import json
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix,ConfusionMatrixDisplay
from app.config import ROOT,Settings
from app.agents.supervisor import route
from app.safety.guardrails import deny_reason
from app.models import Plan
from evals.metrics import latency,prf,ratio
from evals.report_generator import write_report

def evaluate():
    cases=json.loads((ROOT/'evals/datasets/orchestrator.json').read_text())['cases']
    rows=[]; durations=[]; expected=[]; actual=[]
    config=Settings(router_mode='deterministic')
    for c in cases:
        start=time.perf_counter()
        try:
            p=Plan(intent='unsupported',selected_agents=['unsupported'],required_tools=[],requires_rag=False,requires_pin=False,requires_confirmation=False) if deny_reason(c['user_query'],'C1001') else route(c['user_query'],config)
            a={'agents':sorted(p.selected_agents),'tools':sorted(t.name for t in p.required_tools),'rag':p.requires_rag,'pin':p.requires_pin,'confirmation':p.requires_confirmation,'intent':p.intent}
            e={'agents':c['expected_agent_or_agents'],'tools':c['expected_tools'],'rag':c['expected_rag_requirement'],'pin':c['expected_pin_requirement'],'confirmation':c['expected_confirmation_requirement'],'intent':c['expected_intent']}
            expected.append(e); actual.append(a)
            mismatch=[k for k in e if e[k]!=a[k]]
            rows.append(dict(test_id=c['test_id'],query=c['user_query'],expected=e,actual_results=a,status='failed' if mismatch else 'passed',root_cause='Routing mismatch: '+', '.join(mismatch) if mismatch else ''))
        except Exception as exc:
            rows.append(dict(test_id=c['test_id'],status='errored',root_cause=type(exc).__name__))
        durations.append((time.perf_counter()-start)*1000)
    n=len(expected)
    agents=['account','payments','cards','loans','fraud','knowledge','unsupported']
    scores={a:prf([r['agents'] for r in expected],[r['agents'] for r in actual],a) for a in agents}
    tools=set(t for r in expected+actual for t in r['tools'])
    tp=sum(len(set(e['tools'])&set(a['tools'])) for e,a in zip(expected,actual))
    metrics={'intent_accuracy':sum(e['intent']==a['intent'] for e,a in zip(expected,actual))/n,'per_agent':scores,'macro_f1':sum(s['f1'] for s in scores.values())/len(scores),'tool_selection_accuracy':sum(e['tools']==a['tools'] for e,a in zip(expected,actual))/n,'tool_precision':ratio(tp,sum(len(a['tools']) for a in actual)),'tool_recall':ratio(tp,sum(len(e['tools']) for e in expected)),'rag_routing_accuracy':sum(e['rag']==a['rag'] for e,a in zip(expected,actual))/n,'pin_detection_recall':ratio(sum(e['pin'] and a['pin'] for e,a in zip(expected,actual)),sum(e['pin'] for e in expected)),'confirmation_detection_recall':ratio(sum(e['confirmation'] and a['confirmation'] for e,a in zip(expected,actual)),sum(e['confirmation'] for e in expected)),'unsupported_detection_recall':scores['unsupported']['recall'],'multi_agent_routing_accuracy':ratio(sum(e['agents']==a['agents'] for e,a in zip(expected,actual) if len(e['agents'])>1),sum(len(e['agents'])>1 for e in expected)),**latency(durations)}
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(9,4)); ax.bar(agents,[scores[a]['f1'] for a in agents],color='#186da1');ax.set(ylim=(0,1.05),ylabel='F1',title='Deterministic routing baseline');fig.tight_layout();fig.savefig(folder/'agent_performance.png',dpi=140);plt.close(fig)
    labels=agents+['mixed']; matrix=confusion_matrix([e['intent'] for e in expected],[a['intent'] for a in actual],labels=labels)
    metrics['confusion_matrix']={'labels':labels,'values':matrix.tolist()}
    fig,ax=plt.subplots(figsize=(9,7));ConfusionMatrixDisplay(matrix,display_labels=labels).plot(ax=ax,xticks_rotation=45,colorbar=False);fig.tight_layout();fig.savefig(folder/'confusion_matrix.png',dpi=140);plt.close(fig)
    return write_report('orchestrator_eval',metrics,rows,['Deterministic baseline only; not real LLM routing.','Synthetic acceptance queries are not an independent holdout.'])

if __name__=='__main__': evaluate()
