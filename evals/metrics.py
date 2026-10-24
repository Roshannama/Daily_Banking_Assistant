import numpy as np

def ratio(n,d): return n/d if d else None
def latency(values): return {'p50_ms':float(np.percentile(values,50)), 'p95_ms':float(np.percentile(values,95))} if values else {}
def prf(expected,actual,label):
    tp=sum(label in e and label in a for e,a in zip(expected,actual)); fp=sum(label not in e and label in a for e,a in zip(expected,actual)); fn=sum(label in e and label not in a for e,a in zip(expected,actual))
    p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
    return {'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0,'support':tp+fn}
